import os, json, hashlib, re
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Tuple, Any
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import pandas as pd
import faiss
from pymongo import MongoClient
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler, LabelEncoder
from imblearn.over_sampling import SMOTE
from collections import Counter
import shap
import lime
from lime.lime_tabular import LimeTabularExplainer
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import classification_report, confusion_matrix
from tqdm.auto import tqdm
import openai
import warnings
warnings.filterwarnings('ignore')

from config import config

# =======================
# Models
# =======================

class VerificationStatus(Enum):
    AUTO_VERIFIED = "auto_verified"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"

@dataclass
class DetectionResult:
    hallucination: bool
    hallucination_type: str
    hallucination_confidence: float
    bias: bool
    bias_type: str
    bias_confidence: float

@dataclass
class ValidationResult:
    factual_score: float
    coherence_score: float
    consensus_score: float
    status: VerificationStatus
    explanations: Dict[str, str] = field(default_factory=dict)

@dataclass
class SystemOutput:
    hallucination: bool
    hallucination_type: str
    bias: bool
    bias_type: str
    explanation: str
    corrected_response: str
    confidence: float
    status: str
    # Additional fields for detailed frontend display
    gatekeeper_metrics: Dict[str, Any] = field(default_factory=dict)
    rag_agent_responses: Dict[str, Any] = field(default_factory=dict)
    validation_details: Dict[str, Any] = field(default_factory=dict)
    feature_importance: Dict[str, Any] = field(default_factory=dict)
    rule_based_detection: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)

# =======================
# OpenAI Embeddings
# =======================

class OpenAIEmbedder:
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    def encode(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.array([])
        texts = [t[:8000] for t in texts]
        all_emb = []
        for i in range(0, len(texts), 100):
            resp = self.client.embeddings.create(input=texts[i:i+100], model=self.model)
            all_emb.extend([item.embedding for item in resp.data])
        emb = np.array(all_emb, dtype='float32')
        return emb / (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-10)

class TextChunker:
    def __init__(self, size: int = 512, overlap: int = 50):
        self.size, self.overlap = size, overlap

    def chunk(self, text: str) -> List[str]:
        if len(text) <= self.size:
            return [text]
        chunks, start = [], 0
        while start < len(text):
            end = start + self.size
            if end < len(text):
                bp = max(text.rfind('.', start, end), text.rfind('\n', start, end))
                if bp > start:
                    end = bp + 1
            chunks.append(text[start:end].strip())
            start = end - self.overlap
        return [c for c in chunks if c]

# =======================
# MongoDB
# =======================

class MongoDBClient:
    def __init__(self, uri: str, db: str, col: str):
        try:
            import certifi
            self.client = MongoClient(
                uri,
                tlsCAFile=certifi.where(),
                serverSelectionTimeoutMS=10000
            )
            print("✅ Using certifi for SSL")
        except ImportError:
            print("⚠️ certifi not found, using alternative SSL settings")
            self.client = MongoClient(
                uri,
                tlsAllowInvalidCertificates=True,
                serverSelectionTimeoutMS=10000
            )

        # Test connection
        self.client.server_info()

        self.db = self.client[db]
        self.collection = self.db[col]
        self.provisional_kb = self.db["provisional_kb"]
        self.verified_kb = self.db["verified_kb"]

    def fetch_all(self) -> pd.DataFrame:
        data = list(self.collection.find({}))
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)

    def store_provisional(self, record: dict) -> str:
        record["verification_count"] = 1
        return str(self.provisional_kb.insert_one(record).inserted_id)

    def close(self):
        self.client.close()

# =======================
# Gatekeeper with SVM
# =======================

class GatekeeperClassifier:
    def __init__(self, embedder):
        self.embedder = embedder
        
        # Initialize SVM models with RBF kernel (good for high-dimensional data)
        self.hall_clf = SVC(
            kernel='rbf',
            C=10.0,  # Regularization parameter
            gamma='scale',  # Kernel coefficient
            class_weight='balanced',  # Handle imbalanced datasets
            probability=True,  # Enable probability estimates
            random_state=42
        )
        
        self.bias_clf = SVC(
            kernel='rbf',
            C=100.0,  # Much higher C for bias (more aggressive)
            gamma='auto',  # More flexible gamma
            class_weight={0: 1, 1: 5},  # Heavy weight for bias class
            probability=True,
            random_state=42
        )
        
        # Scalers for feature normalization (critical for SVM)
        self.scaler_hall = StandardScaler()
        self.scaler_bias = StandardScaler()
        
        # Store training data for SHAP/LIME
        self.X_train_hall = None
        self.X_train_bias = None
        self.feature_names = None
        
        self.trained = False

    def train(self, df):
        print("🔄 Training Gatekeeper with SVM (RBF kernel)...")
        
        # Prepare features
        texts = [f"{r['user_message']} [SEP] {r['ai_response']}" for _, r in df.iterrows()]
        X = self.embedder.encode(texts)
        
        print(f"📊 Dataset: {len(X)} samples with {X.shape[1]} features")
        
        # Prepare labels
        y_h = (df["label_hallucination"] > 0).astype(int).values
        y_b = (df["label_bias"] > 0).astype(int).values
        
        print(f"📈 Class distribution:")
        print(f"   Hallucination: {np.sum(y_h)} positive ({100*np.mean(y_h):.1f}%), {len(y_h) - np.sum(y_h)} negative")
        print(f"   Bias: {np.sum(y_b)} positive ({100*np.mean(y_b):.1f}%), {len(y_b) - np.sum(y_b)} negative")

        # Train-test split with stratification
        Xtr, Xte, yh_tr, yh_te = train_test_split(
            X, y_h, test_size=0.2, random_state=42, stratify=y_h
        )
        Xtr_b, Xte_b, yb_tr, yb_te = train_test_split(
            X, y_b, test_size=0.2, random_state=42, stratify=y_b
        )

        # Scale features and train hallucination classifier
        print("\n🎯 Training Hallucination Classifier...")
        Xtr_scaled_h = self.scaler_hall.fit_transform(Xtr)
        Xte_scaled_h = self.scaler_hall.transform(Xte)
        self.hall_clf.fit(Xtr_scaled_h, yh_tr)
        
        # For bias: Apply SMOTE if too imbalanced
        print("🎯 Training Bias Classifier...")
        bias_ratio = np.sum(yb_tr) / len(yb_tr)
        
        if bias_ratio < 0.15:  # Less than 15% positive class
            print(f"⚠️  Severe imbalance detected ({bias_ratio*100:.1f}% bias cases)")
            print("   Applying SMOTE oversampling...")
            
            try:
                smote = SMOTE(random_state=42, k_neighbors=min(3, np.sum(yb_tr)-1))
                Xtr_b_resampled, yb_tr_resampled = smote.fit_resample(Xtr_b, yb_tr)
                print(f"   ✓ Resampled: {Counter(yb_tr_resampled)}")
                
                Xtr_scaled_b = self.scaler_bias.fit_transform(Xtr_b_resampled)
                Xte_scaled_b = self.scaler_bias.transform(Xte_b)
                self.bias_clf.fit(Xtr_scaled_b, yb_tr_resampled)
            except Exception as e:
                print(f"   ✗ SMOTE failed: {e}")
                print("   Using original data with extreme class weights...")
                Xtr_scaled_b = self.scaler_bias.fit_transform(Xtr_b)
                Xte_scaled_b = self.scaler_bias.transform(Xte_b)
                self.bias_clf.fit(Xtr_scaled_b, yb_tr)
        else:
            Xtr_scaled_b = self.scaler_bias.fit_transform(Xtr_b)
            Xte_scaled_b = self.scaler_bias.transform(Xte_b)
            self.bias_clf.fit(Xtr_scaled_b, yb_tr)

        # Evaluation with Confusion Matrix
        yh_pred = self.hall_clf.predict(Xte_scaled_h)
        print(f"\n📈 Hallucination Detection Performance:")
        print(classification_report(yh_te, yh_pred, target_names=['No Hallucination', 'Hallucination']))
        
        # Confusion Matrix for Hallucination
        cm_hall = confusion_matrix(yh_te, yh_pred)
        print(f"\n📊 Hallucination Confusion Matrix:")
        print(f"                 Predicted")
        print(f"              No Hall  Hall")
        print(f"Actual No Hall   {cm_hall[0,0]:4d}   {cm_hall[0,1]:4d}")
        print(f"Actual Hall      {cm_hall[1,0]:4d}   {cm_hall[1,1]:4d}")
        
        yb_pred = self.bias_clf.predict(Xte_scaled_b)
        print(f"\n📈 Bias Detection Performance:")
        print(classification_report(yb_te, yb_pred, target_names=['No Bias', 'Bias']))
        
        # Confusion Matrix for Bias
        cm_bias = confusion_matrix(yb_te, yb_pred)
        print(f"\n📊 Bias Confusion Matrix:")
        print(f"                Predicted")
        print(f"            No Bias  Bias")
        print(f"Actual No Bias {cm_bias[0,0]:4d}   {cm_bias[0,1]:4d}")
        print(f"Actual Bias    {cm_bias[1,0]:4d}   {cm_bias[1,1]:4d}")
        
        # Store training data for explainability
        self.X_train_hall = Xtr_scaled_h
        self.X_train_bias = Xtr_scaled_b if not bias_ratio < 0.15 else Xtr_scaled_b
        self.feature_names = [f"emb_{i}" for i in range(Xtr_scaled_h.shape[1])]
        
        # Print model statistics
        print(f"\n📊 Model Statistics:")
        print(f"   Hallucination - Support Vectors: {len(self.hall_clf.support_)}")
        print(f"   Bias - Support Vectors: {len(self.bias_clf.support_)}")
        
        # Warning if bias performance is still poor
        bias_f1 = 2 * (yb_pred == yb_te).sum() / (len(yb_pred) + len(yb_te))
        if bias_f1 < 0.3:
            print(f"\n⚠️  WARNING: Bias detection F1-score is very low ({bias_f1:.2f})")
            print(f"   Consider adding more bias examples to your dataset.")
            print(f"   Current: {np.sum(y_b)} bias cases. Recommended: 40-50+ cases.")
        
        self.trained = True
        print("\n✅ Training completed!")

    def detect(self, user_msg: str, ai_resp: str, use_hybrid=True, precomputed_rule_results=None) -> DetectionResult:
        """
        Hybrid detection combining rule-based heuristics + ML models
        """

        # Step 1: Rule-based detection
        rule_confidence = 0.0
        rule_detected = False
        rule_type = "none"
        rule_results = precomputed_rule_results

        if use_hybrid and rule_results is None:
            try:
                from hybrid_detection import get_hybrid_detector
                hybrid = get_hybrid_detector()
                rule_results = hybrid.detect(user_msg, ai_resp)
            except Exception as e:
                print(f"⚠️ Hybrid detection error: {e}")
                rule_results = {"detected": False, "confidence": 0.0, "checks": {}}

        # Process rule results
        if rule_results and rule_results.get("detected"):
            print(f"\n🔍 Rule-based detection: {rule_results.get('confidence', 0.0):.2%}")
            rule_detected = True
            rule_confidence = rule_results["confidence"]

            for rule in rule_results.get("matched_rules", []):
                if "factual" in rule:
                    rule_type = "fabricated"
                elif "temporal" in rule:
                    rule_type = "temporal"
                elif "logical" in rule:
                    rule_type = "logical"
                elif "exaggeration" in rule:
                    rule_type = "exaggeration"

            # High confidence rule - return immediately
            if rule_confidence >= 0.85:
                print(f"✅ High confidence rule ({rule_confidence:.2%}) - returning")
                return DetectionResult(
                    hallucination=True,
                    hallucination_type=rule_type,
                    hallucination_confidence=rule_confidence,
                    bias=False,
                    bias_type="none",
                    bias_confidence=0.0
                )

        # Step 2: ML detection
        if not self.trained:
            if rule_detected:
                return DetectionResult(
                    hallucination=True,
                    hallucination_type=rule_type,
                    hallucination_confidence=rule_confidence,
                    bias=False,
                    bias_type="none",
                    bias_confidence=0.0
                )
            return DetectionResult(
                hallucination=False,
                hallucination_type="none",
                hallucination_confidence=0.0,
                bias=False,
                bias_type="none",
                bias_confidence=0.0
            )

        # Generate features
        feat = self.embedder.encode([f"{user_msg} [SEP] {ai_resp}"])
        feat_scaled_h = self.scaler_hall.transform(feat)
        feat_scaled_b = self.scaler_bias.transform(feat)

        hp = self.hall_clf.predict_proba(feat_scaled_h)[0]
        bp = self.bias_clf.predict_proba(feat_scaled_b)[0]

        # Combine
        ml_confidence = float(hp[1])
        final_confidence = max(ml_confidence, rule_confidence)
        threshold = 0.35 if rule_detected else 0.5
        final_detected = final_confidence > threshold

        # Type inference
        if rule_type == "none" and final_detected:
            if ml_confidence > 0.8:
                ml_type = "fabricated fact"
            elif ml_confidence > 0.65:
                ml_type = "exaggeration"
            else:
                ml_type = "misinterpreted context"
        else:
            ml_type = rule_type if rule_type != "none" else "none"

        return DetectionResult(
            hallucination=bool(final_detected),
            hallucination_type=ml_type,
            hallucination_confidence=final_confidence,
            bias=bool(bp[1] > 0.5),
            bias_type="detected" if bp[1] > 0.5 else "none",
            bias_confidence=float(bp[1])
        )
    
    def explain_prediction_shap(self, user_msg: str, ai_resp: str, model_type: str = "hallucination"):
        """
        Generate SHAP explanation for a prediction
        model_type: 'hallucination' or 'bias'
        """
        if not self.trained:
            print("⚠️ Model not trained yet!")
            return None
        
        # Generate features
        feat = self.embedder.encode([f"{user_msg} [SEP] {ai_resp}"])
        
        # Select appropriate model and scaler
        if model_type == "hallucination":
            feat_scaled = self.scaler_hall.transform(feat)
            model = self.hall_clf
            background = self.X_train_hall[:100]  # Use subset for speed
        else:
            feat_scaled = self.scaler_bias.transform(feat)
            model = self.bias_clf
            background = self.X_train_bias[:100]
        
        try:
            print(f"\n🔍 Generating SHAP explanation for {model_type} detection...")
            
            # Create SHAP explainer (KernelExplainer for SVM)
            explainer = shap.KernelExplainer(
                lambda x: model.predict_proba(x)[:, 1],
                background,
                link="identity"
            )
            
            # Calculate SHAP values
            shap_values = explainer.shap_values(feat_scaled, nsamples=100)
            
            # Show top features
            feature_importance = np.abs(shap_values[0])
            top_indices = np.argsort(feature_importance)[-10:][::-1]
            
            print(f"\n📊 Top 10 Most Important Features:")
            for i, idx in enumerate(top_indices, 1):
                print(f"   {i}. Feature {idx}: {feature_importance[idx]:.4f}")
            
            print(f"\n✅ SHAP explanation complete. Base value: {explainer.expected_value:.4f}")
            print(f"   Prediction contribution: {shap_values[0].sum():.4f}")
            
            return {
                "shap_values": shap_values[0],
                "base_value": explainer.expected_value,
                "top_features": top_indices.tolist(),
                "feature_importance": feature_importance[top_indices].tolist()
            }
            
        except Exception as e:
            print(f"❌ SHAP explanation failed: {str(e)}")
            return None
    
    def explain_prediction_lime(self, user_msg: str, ai_resp: str, model_type: str = "hallucination"):
        """
        Generate LIME explanation for a prediction
        model_type: 'hallucination' or 'bias'
        """
        if not self.trained:
            print("⚠️ Model not trained yet!")
            return None
        
        # Generate features
        feat = self.embedder.encode([f"{user_msg} [SEP] {ai_resp}"])
        
        # Select appropriate model and scaler
        if model_type == "hallucination":
            feat_scaled = self.scaler_hall.transform(feat)
            model = self.hall_clf
            training_data = self.X_train_hall
        else:
            feat_scaled = self.scaler_bias.transform(feat)
            model = self.bias_clf
            training_data = self.X_train_bias
        
        try:
            print(f"\n🔍 Generating LIME explanation for {model_type} detection...")
            
            # Create LIME explainer
            explainer = LimeTabularExplainer(
                training_data,
                feature_names=self.feature_names,
                class_names=['Negative', 'Positive'],
                mode='classification',
                random_state=42
            )
            
            # Generate explanation
            explanation = explainer.explain_instance(
                feat_scaled[0],
                model.predict_proba,
                num_features=10,
                top_labels=1
            )
            
            # Get feature weights
            feature_weights = explanation.as_list(label=1)
            
            print(f"\n📊 Top 10 Features by LIME:")
            for i, (feature, weight) in enumerate(feature_weights, 1):
                direction = "→ Positive" if weight > 0 else "→ Negative"
                print(f"   {i}. {feature}: {weight:.4f} {direction}")
            
            print(f"\n✅ LIME explanation complete.")
            print(f"   Prediction probability: {model.predict_proba(feat_scaled)[0][1]:.4f}")
            
            return {
                "feature_weights": feature_weights,
                "prediction_proba": model.predict_proba(feat_scaled)[0].tolist(),
                "intercept": explanation.intercept[1]
            }
            
        except Exception as e:
            print(f"❌ LIME explanation failed: {str(e)}")
            return None

# =======================
# Multi-Agent RAG
# =======================

class VectorKB:
    def __init__(self, name: str, embedder, dim: int = 1536):
        self.name, self.embedder = name, embedder
        self.index = faiss.IndexFlatIP(dim)
        self.docs = []

    def add(self, docs: List[dict]):
        if not docs:
            return
        texts = [f"{d.get('user_message', '')} {d.get('ai_response', '')}" for d in docs]
        self.index.add(self.embedder.encode(texts))
        self.docs.extend(docs)

    def search(self, query: str, k: int = 5):
        if not self.index.ntotal:
            return []
        scores, idx = self.index.search(self.embedder.encode([query]), min(k, self.index.ntotal))
        return [(self.docs[i], scores[0][j]) for j, i in enumerate(idx[0]) if i < len(self.docs)]

class RAGAgent:
    def __init__(self, cat: str, kb: VectorKB):
        self.cat, self.kb = cat, kb

    def retrieve(self, q: str, resp: str, k: int = 5):
        results = self.kb.search(f"{q} {resp}", k)
        if not results:
            return resp, "No matches", []
        draft = results[0][0].get("corrected_response", results[0][0].get("ai_response", resp))
        return draft, f"{len(results)} matches, top: {results[0][1]:.2f}", [r[0] for r in results]

class SmartRouter:
    MAP = {
        "factual": ["factual", "fabricated"],
        "logical": ["logical"],
        "temporal": ["temporal"],
        "bias": ["bias"]
    }

    @classmethod
    def route(cls, det: DetectionResult) -> str:
        if det.bias:
            return "bias"
        for cat, kw in cls.MAP.items():
            if any(k in det.hallucination_type.lower() for k in kw):
                return cat
        return "factual"

# =======================
# Enhanced Consensus Validators
# =======================

class LLMValidator(ABC):
    @abstractmethod
    def validate(self, orig: str, corr: str, ctx: str) -> Tuple[float, str]:
        pass

class OpenAIValidator(LLMValidator):
    """
    OpenAI validator that can use different models
    """
    def __init__(self, key: str, model: str = "gpt-4o-mini", name: str = "OpenAI"):
        self.client = openai.OpenAI(api_key=key) if key else None
        self.model = model
        self.name = name

    def validate(self, orig: str, corr: str, ctx: str) -> Tuple[float, str]:
        if not self.client:
            return 0.75, f"{self.name} not configured"
        
        try:
            prompt = f"""Analyze the quality of this correction carefully.

ORIGINAL RESPONSE: {orig[:500]}

CORRECTED RESPONSE: {corr[:500]}

CONTEXT/REASONING: {ctx}

Rate the correction on a scale of 0.0 to 1.0 based on:
- Factual accuracy improvement (0.4 weight)
- Clarity and coherence (0.3 weight)  
- Relevance to the issue (0.3 weight)

Be critical and use the full scale:
- 0.0-0.3: Poor correction, introduces new issues
- 0.3-0.5: Marginal improvement or lateral change
- 0.5-0.7: Good correction with minor issues
- 0.7-0.9: Excellent correction, clear improvement
- 0.9-1.0: Perfect correction

Return ONLY a JSON object with this exact format:
{{"score": 0.XX, "reason": "brief explanation"}}"""

            resp = self.client.chat.completions.create(
                model=self.model,
                max_tokens=150,
                temperature=0.2,  # Lower for more consistent scoring
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = resp.choices[0].message.content.strip()
            # Clean up markdown formatting
            content = re.sub(r'```json\s*|\s*```', '', content)
            
            result = json.loads(content)
            score = float(result.get("score", 0.5))
            reason = result.get("reason", "No explanation provided")
            
            # Clamp score to valid range
            score = max(0.0, min(1.0, score))
            
            print(f"  ✓ {self.name} ({self.model}): {score:.2f} - {reason[:80]}")
            return score, reason
            
        except json.JSONDecodeError as e:
            print(f"  ✗ {self.name} JSON parse error: {content[:100]}")
            # Fallback: try to extract score from text
            match = re.search(r'(?:score|rating).*?(\d+\.?\d*)', content, re.IGNORECASE)
            if match:
                score = float(match.group(1))
                if score > 1.0:  # Handle percentage
                    score = score / 100
                return max(0.0, min(1.0, score)), "Extracted from text"
            return 0.6, f"Parse error: {str(e)[:50]}"
            
        except Exception as e:
            print(f"  ✗ {self.name} error: {str(e)[:100]}")
            return 0.5, f"Error: {str(e)[:50]}"


class HeuristicValidator(LLMValidator):
    """
    Fallback validator when LLMs are unavailable
    Uses text-based heuristics to provide reasonable scores
    """
    
    def validate(self, orig: str, corr: str, ctx: str) -> Tuple[float, str]:
        score = 0.5
        reasons = []
        
        # Length comparison
        len_diff = abs(len(corr) - len(orig)) / max(len(orig), 1)
        if len_diff < 0.1:
            score += 0.1
            reasons.append("similar length")
        elif len_diff > 0.5:
            score -= 0.1
            reasons.append("significant length change")
        
        # Check if correction adds specific details
        if any(word in corr.lower() for word in ["specifically", "according to", "based on", "verified"]):
            score += 0.15
            reasons.append("adds specificity")
        
        # Check for hedging language (good for reducing hallucinations)
        if any(word in corr.lower() for word in ["approximately", "around", "estimated", "likely", "may"]):
            score += 0.1
            reasons.append("appropriate hedging")
        
        # Penalize if correction seems to just rephrase
        orig_words = set(orig.lower().split())
        corr_words = set(corr.lower().split())
        overlap = len(orig_words & corr_words) / max(len(orig_words), 1)
        if overlap > 0.8:
            score -= 0.15
            reasons.append("minimal change")
        
        # Bonus if context mentions verification
        if "match" in ctx.lower() or "verified" in ctx.lower():
            score += 0.1
            reasons.append("verified context")
        
        score = max(0.2, min(0.9, score))
        return score, " | ".join(reasons) if reasons else "heuristic analysis"


# =======================
# Enhanced Consensus Engine with Dual OpenAI Models
# =======================

class ConsensusEngine:
    def __init__(self, vals: Dict[str, LLMValidator]):
        self.vals = vals
        
    def validate(self, orig: str, corr: str, ctx: str = "") -> ValidationResult:
        """
        Enhanced consensus validation with better scoring logic
        Uses two different OpenAI models for cross-validation
        """
        print(f"\n🔍 Running consensus validation with dual OpenAI models...")
        
        results = {}
        explanations = {}
        
        # Run validators in parallel with timeout
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(v.validate, orig, corr, ctx): name 
                for name, v in self.vals.items()
            }
            
            for future in as_completed(futures, timeout=35):
                name = futures[future]
                try:
                    score, explanation = future.result(timeout=30)
                    results[name] = score
                    explanations[name] = explanation
                except Exception as e:
                    print(f"  ✗ {name} timeout/error: {str(e)[:50]}")
                    # Use neutral score on error, not 0.5 always
                    results[name] = 0.65
                    explanations[name] = f"Validation error: {str(e)[:50]}"
        
        # Calculate consensus with weighted average
        if len(results) == 0:
            consensus_score = 0.5
            print("  ⚠️ No validators succeeded, using default 0.5")
        elif len(results) == 1:
            consensus_score = list(results.values())[0]
            print(f"  ⚠️ Only one validator succeeded: {consensus_score:.2f}")
        else:
            # For dual OpenAI models: give equal weight to both, lower weight to heuristic
            weights = {
                "gpt4o-mini": 0.45,      # GPT-4o-mini
                "gpt35-turbo": 0.45,     # GPT-3.5-turbo  
                "heuristic": 0.10        # Fallback heuristic
            }
            
            consensus_score = sum(
                results[k] * weights.get(k, 0.33) 
                for k in results
            ) / sum(weights.get(k, 0.33) for k in results)
            
            print(f"  📊 Consensus: {consensus_score:.2f} (from {len(results)} validators)")
            
            # Show agreement/disagreement between the two models
            if "gpt4o-mini" in results and "gpt35-turbo" in results:
                diff = abs(results["gpt4o-mini"] - results["gpt35-turbo"])
                if diff < 0.1:
                    print(f"  ✅ Strong agreement between models (diff: {diff:.3f})")
                elif diff < 0.2:
                    print(f"  ⚠️  Moderate agreement (diff: {diff:.3f})")
                else:
                    print(f"  ⚠️  Significant disagreement (diff: {diff:.3f})")
        
        # Determine verification status with clearer thresholds
        if consensus_score >= 0.75:
            status = VerificationStatus.AUTO_VERIFIED
            status_emoji = "✅"
        elif consensus_score >= 0.45:
            status = VerificationStatus.NEEDS_REVIEW
            status_emoji = "⚠️"
        else:
            status = VerificationStatus.REJECTED
            status_emoji = "❌"
        
        print(f"  {status_emoji} Status: {status.value} (score: {consensus_score:.2%})")
        
        # For dual OpenAI setup, use both scores for factual and coherence
        return ValidationResult(
            factual_score=results.get("gpt4o-mini", results.get("gpt35-turbo", 0.5)),
            coherence_score=results.get("gpt35-turbo", results.get("gpt4o-mini", 0.5)),
            consensus_score=consensus_score,
            status=status,
            explanations=explanations
        )

# =======================
# Pipeline
# =======================

class Pipeline:
    def __init__(self):
        print("🚀 Initializing Multi-Agent RAG Pipeline with Dual OpenAI Consensus...")

        # Initialize embedder
        if not config.OPENAI_API_KEY:
            print("⚠️ OpenAI API key not found. Pipeline will run in limited mode.")
            self.embedder = None
            self.gate = None
            self.agents = {}
            self.consensus = None
            self.db = None
            return

        self.embedder = OpenAIEmbedder(config.OPENAI_API_KEY)
        print("✅ OpenAI Embedder initialized")

        # Initialize MongoDB
        try:
            self.db = MongoDBClient(config.MONGO_URI, config.DB_NAME, config.COLLECTION)
            df = self.db.fetch_all()
            print(f"✅ Loaded {len(df)} records from MongoDB")
        except Exception as e:
            print(f"⚠️ MongoDB unavailable: {str(e)[:100]}")
            df = pd.DataFrame()
            self.db = None

        # Initialize Gatekeeper
        self.gate = GatekeeperClassifier(self.embedder)
        if len(df) > 10:
            self.gate.train(df)
        else:
            print("⚠️ Insufficient data for training. Using fallback detection.")

        # Build Knowledge Bases
        kbs = {c: VectorKB(c, self.embedder, config.EMBEDDING_DIM)
               for c in ["factual", "logical", "temporal", "bias"]}

        cat_docs = {c: [] for c in kbs}
        for _, r in df.iterrows():
            det = DetectionResult(
                bool(r.get("label_hallucination", 0) > 0),
                str(r.get("hallucination_type", "none")),
                0.9,
                bool(r.get("label_bias", 0) > 0),
                str(r.get("bias_type", "none")),
                0.9
            )
            cat_docs[SmartRouter.route(det)].append(r.to_dict())

        print("📚 Building Knowledge Bases...")
        for c, docs in cat_docs.items():
            if docs:
                print(f"  {c}: {len(docs)} documents")
                kbs[c].add(docs)

        self.agents = {c: RAGAgent(c, kb) for c, kb in kbs.items()}

        # Initialize Enhanced Consensus Engine with DUAL OpenAI Models
        validators = {}
        
        if config.OPENAI_API_KEY:
            # Use two different OpenAI models for consensus
            validators["gpt4o-mini"] = OpenAIValidator(
                config.OPENAI_API_KEY, 
                model="gpt-4o-mini",
                name="GPT-4o-mini"
            )
            validators["gpt35-turbo"] = OpenAIValidator(
                config.OPENAI_API_KEY,
                model="gpt-3.5-turbo", 
                name="GPT-3.5-turbo"
            )
            print("✅ Dual OpenAI validators enabled:")
            print("   - GPT-4o-mini (primary)")
            print("   - GPT-3.5-turbo (secondary)")
        else:
            print("⚠️ No OpenAI API key provided, using heuristic validator")
            validators["heuristic"] = HeuristicValidator()
        
        self.consensus = ConsensusEngine(validators)
        print("✅ Enhanced Dual-Model Consensus Engine ready")

        print("✅ Multi-Agent RAG Pipeline ready!")

    def process(self, user_msg: str, ai_resp: str) -> SystemOutput:
        if not self.embedder:
            return SystemOutput(
                hallucination=False,
                hallucination_type="none",
                bias=False,
                bias_type="none",
                explanation="Pipeline not fully initialized. OpenAI API key required.",
                corrected_response=ai_resp,
                confidence=0.0,
                status="auto_verified"
            )

        # Step 1: Gatekeeper Detection
        det = self.gate.detect(user_msg, ai_resp)

        gatekeeper_metrics = {
            "hallucination_detected": det.hallucination,
            "hallucination_type": det.hallucination_type,
            "hallucination_confidence": det.hallucination_confidence,
            "bias_detected": det.bias,
            "bias_type": det.bias_type,
            "bias_confidence": det.bias_confidence
        }

        if not det.hallucination and not det.bias:
            return SystemOutput(
                hallucination=False,
                hallucination_type="none",
                bias=False,
                bias_type="none",
                explanation="Response appears clean - no hallucination or bias detected",
                corrected_response=ai_resp,
                confidence=1 - max(det.hallucination_confidence, det.bias_confidence),
                status="auto_verified",
                gatekeeper_metrics=gatekeeper_metrics,
                rag_agent_responses={},
                validation_details={}
            )

        # Step 2: Route to appropriate RAG agent
        cat = SmartRouter.route(det)
        draft, rag_exp, retrieved_docs = self.agents[cat].retrieve(user_msg, ai_resp, config.TOP_K)

        rag_agent_responses = {
            "category": cat,
            "explanation": rag_exp,
            "corrected_response": draft,
            "retrieved_count": len(retrieved_docs),
            "top_matches": [
                {
                    "user_message": doc.get("user_message", ""),
                    "ai_response": doc.get("ai_response", "")
                }
                for doc in retrieved_docs[:3]
            ]
        }

        # Step 3: Enhanced Dual-Model Consensus Validation
        val = self.consensus.validate(ai_resp, draft, rag_exp)

        validation_details = {
            "factual_score": val.factual_score,
            "coherence_score": val.coherence_score,
            "consensus_score": val.consensus_score,
            "status": val.status.value,
            "explanations": val.explanations
        }

        # Store provisional if auto-verified
        if val.status == VerificationStatus.AUTO_VERIFIED and self.db:
            try:
                self.db.store_provisional({
                    "user_message": user_msg,
                    "original": ai_resp,
                    "corrected": draft,
                    "score": val.consensus_score,
                    "category": cat
                })
            except:
                pass

        return SystemOutput(
            det.hallucination,
            det.hallucination_type,
            det.bias,
            det.bias_type,
            f"{cat} | H:{det.hallucination_confidence:.2f} | {rag_exp} | Cons:{val.consensus_score:.2f}",
            draft if val.status != VerificationStatus.REJECTED else ai_resp,
            val.consensus_score,
            val.status.value,
            gatekeeper_metrics=gatekeeper_metrics,
            rag_agent_responses=rag_agent_responses,
            validation_details=validation_details
        )

# =======================
# Initialize Pipeline
# =======================

pipeline = Pipeline()