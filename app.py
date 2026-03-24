from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
from pipeline import pipeline, SmartRouter
import json
import time

app = Flask(__name__, static_folder='.')
CORS(app)  # Enable CORS

@app.route("/")
def index():
    return send_from_directory('.', 'frontend.html')

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "okay"})

# Individual Agent Routes

@app.route("/api/agent/gatekeeper", methods=["POST"])
def agent_gatekeeper():
    """Gatekeeper Agent - Detects hallucinations and bias"""
    data = request.json
    if not data or not data.get("user_message") or not data.get("ai_response"):
        return jsonify({"error": "Missing fields"}), 400

    try:
        if not pipeline.gate:
            return jsonify({"error": "Gatekeeper not initialized"}), 503

        det = pipeline.gate.detect(data["user_message"], data["ai_response"])
        return jsonify({
            "agent": "gatekeeper",
            "hallucination_detected": bool(det.hallucination),
            "hallucination_type": str(det.hallucination_type),
            "hallucination_confidence": float(det.hallucination_confidence),
            "bias_detected": bool(det.bias),
            "bias_type": str(det.bias_type),
            "bias_confidence": float(det.bias_confidence)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/agent/router", methods=["POST"])
def agent_router():
    """SmartRouter Agent - Routes to appropriate RAG agent"""
    data = request.json
    if not data:
        return jsonify({"error": "Invalid request"}), 400

    try:
        # Expect detection result
        from pipeline import DetectionResult
        det = DetectionResult(
            hallucination=data.get("hallucination", False),
            hallucination_type=data.get("hallucination_type", "none"),
            hallucination_confidence=data.get("hallucination_confidence", 0.0),
            bias=data.get("bias", False),
            bias_type=data.get("bias_type", "none"),
            bias_confidence=data.get("bias_confidence", 0.0)
        )
        category = SmartRouter.route(det)
        return jsonify({
            "agent": "smartrouter",
            "category": category,
            "routing_logic": f"Routed to '{category}' based on detection type"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/agent/vectorkb/<category>", methods=["POST"])
def agent_vectorkb(category):
    """Vector Knowledge Base Agent - Retrieves similar cases"""
    data = request.json
    if not data or not data.get("query"):
        return jsonify({"error": "Missing query"}), 400

    try:
        if category not in pipeline.agents:
            return jsonify({"error": f"Unknown category: {category}"}), 400

        kb = pipeline.agents[category].kb
        results = kb.search(data["query"], data.get("k", 5))

        return jsonify({
            "agent": "vectorkb",
            "category": category,
            "total_docs": kb.index.ntotal,
            "retrieved_count": len(results),
            "top_matches": [
                {
                    "user_message": doc.get("user_message", ""),
                    "ai_response": doc.get("ai_response", ""),
                    "similarity_score": float(score)
                }
                for doc, score in results[:3]
            ]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/agent/rag/<category>", methods=["POST"])
def agent_rag(category):
    """RAG Agent - Generates correction based on retrieved context"""
    data = request.json
    if not data or not data.get("user_message") or not data.get("ai_response"):
        return jsonify({"error": "Missing fields"}), 400

    try:
        if category not in pipeline.agents:
            return jsonify({"error": f"Unknown category: {category}"}), 400

        agent = pipeline.agents[category]
        draft, explanation, retrieved_docs = agent.retrieve(
            data["user_message"],
            data["ai_response"],
            data.get("k", 5)
        )

        return jsonify({
            "agent": "rag",
            "category": category,
            "corrected_response": draft,
            "explanation": explanation,
            "retrieved_count": len(retrieved_docs)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/agent/validator/openai", methods=["POST"])
def agent_validator_openai():
    """OpenAI Validator Agent - Validates factual accuracy"""
    data = request.json
    if not data or not data.get("original") or not data.get("corrected"):
        return jsonify({"error": "Missing fields"}), 400

    try:
        validator = pipeline.consensus.vals.get("openai")
        if not validator:
            return jsonify({"error": "OpenAI validator not configured"}), 503

        score, explanation = validator.validate(
            data["original"],
            data["corrected"],
            data.get("context", "")
        )

        return jsonify({
            "agent": "openai_validator",
            "factual_score": score,
            "explanation": explanation
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/agent/validator/gemini", methods=["POST"])
def agent_validator_gemini():
    """Gemini Validator Agent - Validates coherence"""
    data = request.json
    if not data or not data.get("original") or not data.get("corrected"):
        return jsonify({"error": "Missing fields"}), 400

    try:
        validator = pipeline.consensus.vals.get("gemini")
        if not validator:
            return jsonify({"error": "Gemini validator not configured"}), 503

        score, explanation = validator.validate(
            data["original"],
            data["corrected"],
            data.get("context", "")
        )

        return jsonify({
            "agent": "gemini_validator",
            "coherence_score": score,
            "explanation": explanation
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/agent/consensus", methods=["POST"])
def agent_consensus():
    """Consensus Engine - Combines validator scores"""
    data = request.json
    if not data or not data.get("original") or not data.get("corrected"):
        return jsonify({"error": "Missing fields"}), 400

    try:
        validation = pipeline.consensus.validate(
            data["original"],
            data["corrected"],
            data.get("context", "")
        )

        return jsonify({
            "agent": "consensus",
            "factual_score": validation.factual_score,
            "coherence_score": validation.coherence_score,
            "consensus_score": validation.consensus_score,
            "status": validation.status.value,
            "explanations": validation.explanations
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/feature-importance", methods=["GET"])
def feature_importance():
    """Get feature importance from all models"""
    try:
        if not pipeline.gate:
            return jsonify({"error": "Pipeline not initialized"}), 503

        importance = pipeline.gate.get_feature_importance()
        return jsonify(importance), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Streaming Pipeline Endpoint

@app.route("/api/pipeline/stream", methods=["POST"])
def pipeline_stream():
    """Real-time streaming pipeline with step-by-step updates"""
    data = request.json
    if not data or not data.get("user_message") or not data.get("ai_response"):
        return jsonify({"error": "Missing fields"}), 400

    user_msg = data["user_message"]
    ai_resp = data["ai_response"]

    def generate():
        try:
            # Step 1: Gatekeeper
            yield f"data: {json.dumps({'step': 'gatekeeper', 'status': 'processing', 'message': 'Analyzing for hallucinations and bias...'})}\n\n"
            time.sleep(0.3)

            if not pipeline.gate:
                yield f"data: {json.dumps({'step': 'error', 'message': 'Pipeline not initialized'})}\n\n"
                return

            # Get rule-based detection first
            try:
                from hybrid_detection import get_hybrid_detector
                hybrid = get_hybrid_detector()
                rule_results = hybrid.detect(user_msg, ai_resp)
                print(f"\n📊 Streaming endpoint got rule results: {rule_results.get('detected')}, confidence: {rule_results.get('confidence')}")
            except Exception as e:
                print(f"⚠️ Streaming endpoint hybrid detection failed: {e}")
                rule_results = {"detected": False, "confidence": 0.0, "checks": {}}

            # Pass precomputed rule results to avoid re-running detection
            det = pipeline.gate.detect(user_msg, ai_resp, precomputed_rule_results=rule_results)

            # Get feature importance
            try:
                feature_importance = pipeline.gate.get_feature_importance()
            except Exception:
                feature_importance = {}

            gatekeeper_result = {
                "step": "gatekeeper",
                "status": "complete",
                "data": {
                    "hallucination_detected": bool(det.hallucination),
                    "hallucination_type": str(det.hallucination_type),
                    "hallucination_confidence": float(det.hallucination_confidence),
                    "bias_detected": bool(det.bias),
                    "bias_type": str(det.bias_type),
                    "bias_confidence": float(det.bias_confidence),
                    "rule_based_detection": rule_results,
                    "feature_importance": feature_importance
                }
            }
            yield f"data: {json.dumps(gatekeeper_result)}\n\n"

            # ChatGPT Layer 1: Validate Gatekeeper (logged, not shown in frontend)
            try:
                from chatgpt_finetuner import get_chatgpt_finetuner
                finetuner = get_chatgpt_finetuner()
                gatekeeper_validation = finetuner.validate_gatekeeper_output(
                    user_msg, ai_resp, gatekeeper_result["data"]
                )
            except Exception as e:
                print(f"⚠️ ChatGPT gatekeeper validation skipped: {e}")

            # Early exit if clean
            if not det.hallucination and not det.bias:
                yield f"data: {json.dumps({'step': 'complete', 'status': 'clean', 'message': 'Response is clean - no issues detected', 'corrected_response': ai_resp})}\n\n"
                return

            # Step 2: SmartRouter
            time.sleep(0.3)
            yield f"data: {json.dumps({'step': 'router', 'status': 'processing', 'message': 'Routing to appropriate RAG agent...'})}\n\n"

            category = SmartRouter.route(det)
            router_result = {
                "step": "router",
                "status": "complete",
                "data": {"category": category}
            }
            yield f"data: {json.dumps(router_result)}\n\n"

            # Step 3: Vector KB Search
            time.sleep(0.3)
            yield f"data: {json.dumps({'step': 'vectorkb', 'status': 'processing', 'message': f'Searching {category} knowledge base...'})}\n\n"

            kb = pipeline.agents[category].kb
            query = f"{user_msg} {ai_resp}"
            results = kb.search(query, 5)

            vectorkb_result = {
                "step": "vectorkb",
                "status": "complete",
                "data": {
                    "category": category,
                    "retrieved_count": len(results),
                    "top_matches": [
                        {
                            "user_message": doc.get("user_message", ""),
                            "ai_response": doc.get("ai_response", ""),
                            "similarity_score": float(score)
                        }
                        for doc, score in results[:3]
                    ]
                }
            }
            yield f"data: {json.dumps(vectorkb_result)}\n\n"

            # Step 4: RAG Agent
            time.sleep(0.3)
            yield f"data: {json.dumps({'step': 'rag', 'status': 'processing', 'message': 'Generating correction...'})}\n\n"

            agent = pipeline.agents[category]
            draft, rag_exp, retrieved_docs = agent.retrieve(user_msg, ai_resp, 5)

            rag_result = {
                "step": "rag",
                "status": "complete",
                "data": {
                    "corrected_response": draft,
                    "explanation": rag_exp
                }
            }
            yield f"data: {json.dumps(rag_result)}\n\n"

            # ChatGPT Layer 2: Validate RAG Output (logged, not shown in frontend)
            try:
                rag_validation = finetuner.validate_rag_output(
                    user_msg, ai_resp, draft, retrieved_docs
                )
                # Use improved correction if available
                if rag_validation.get('improved_correction') and not rag_validation.get('is_accurate'):
                    draft = rag_validation['improved_correction']
                    print(f"✅ Using ChatGPT-improved RAG correction")
            except Exception as e:
                print(f"⚠️ ChatGPT RAG validation skipped: {e}")

            # Step 5: OpenAI Validator
            time.sleep(0.5)
            yield f"data: {json.dumps({'step': 'validator_openai', 'status': 'processing', 'message': 'Validating with OpenAI...'})}\n\n"

            openai_val = pipeline.consensus.vals.get("openai")
            openai_score, openai_exp = openai_val.validate(ai_resp, draft, rag_exp) if openai_val else (0.75, "Not configured")

            openai_result = {
                "step": "validator_openai",
                "status": "complete",
                "data": {
                    "factual_score": float(openai_score),
                    "explanation": str(openai_exp)
                }
            }
            yield f"data: {json.dumps(openai_result)}\n\n"

            # Step 6: Gemini Validator
            time.sleep(0.5)
            yield f"data: {json.dumps({'step': 'validator_gemini', 'status': 'processing', 'message': 'Validating with Gemini...'})}\n\n"

            gemini_val = pipeline.consensus.vals.get("gemini")
            gemini_score, gemini_exp = gemini_val.validate(ai_resp, draft, rag_exp) if gemini_val else (0.75, "Not configured")

            gemini_result = {
                "step": "validator_gemini",
                "status": "complete",
                "data": {
                    "coherence_score": float(gemini_score),
                    "explanation": str(gemini_exp)
                }
            }
            yield f"data: {json.dumps(gemini_result)}\n\n"

            # Step 7: Consensus
            time.sleep(0.3)
            yield f"data: {json.dumps({'step': 'consensus', 'status': 'processing', 'message': 'Calculating consensus...'})}\n\n"

            val = pipeline.consensus.validate(ai_resp, draft, rag_exp)

            consensus_result = {
                "step": "consensus",
                "status": "complete",
                "data": {
                    "factual_score": float(val.factual_score),
                    "coherence_score": float(val.coherence_score),
                    "consensus_score": float(val.consensus_score),
                    "status": str(val.status.value),
                    "explanations": val.explanations
                }
            }
            yield f"data: {json.dumps(consensus_result)}\n\n"

            # ChatGPT Layer 3: Validate Consensus Output (logged, not shown in frontend)
            try:
                consensus_validation = finetuner.validate_consensus_output(
                    ai_resp,
                    draft,
                    {
                        'factual': val.factual_score,
                        'coherence': val.coherence_score,
                        'consensus': val.consensus_score
                    }
                )
                print(f"✅ ChatGPT consensus validation complete")
            except Exception as e:
                print(f"⚠️ ChatGPT consensus validation skipped: {e}")

            # Step 8: OpenAI Corrector (for fine-tuning only, not shown in frontend)
            try:
                from openai_corrector import get_openai_corrector
                corrector = get_openai_corrector()

                # Generate GPT-4 correction (logged for fine-tuning, not displayed)
                gpt4_correction = corrector.generate_correction(
                    user_message=user_msg,
                    hallucinated_response=ai_resp,
                    detection_type=det.hallucination_type,
                    detection_reason=rule_results.get("reasons", ["Detected by hybrid system"])[0] if rule_results and rule_results.get("detected") else "ML detection",
                    retrieved_context=rag_exp
                )

                # Log for fine-tuning
                corrector.log_for_fine_tuning(
                    user_message=user_msg,
                    hallucinated_response=ai_resp,
                    corrected_response=gpt4_correction.get("corrected_response", draft),
                    detection_info={
                        "type": det.hallucination_type,
                        "confidence": det.hallucination_confidence,
                        "reason": rule_results.get("reasons", ["hybrid detection"])[0] if rule_results and rule_results.get("detected") else "ML detection"
                    },
                    validation_score=val.consensus_score
                )

                print(f"\n🤖 GPT-4 Correction (for fine-tuning):")
                print(f"   Method: {gpt4_correction.get('method', 'none')}")
                print(f"   Tokens: {gpt4_correction.get('tokens_used', 0)}")
                print(f"   Explanation: {gpt4_correction.get('explanation', '')}")
                print(f"   ✅ Logged to fine_tuning_data.jsonl")

            except Exception as e:
                print(f"⚠️ GPT-4 correction failed: {e}")

            # ChatGPT Layer 4: Generate Gold Standard Output (logged, not shown in frontend)
            try:
                gold_standard = finetuner.generate_gold_standard_output(
                    user_msg,
                    ai_resp,
                    draft
                )

                # Use gold standard if quality score is very high
                if gold_standard.get('quality_score', 0) > 0.9:
                    draft = gold_standard['gold_standard_response']
                    print(f"✅ Using ChatGPT gold standard response (quality: {gold_standard.get('quality_score'):.2f})")
                else:
                    print(f"✅ ChatGPT gold standard logged (quality: {gold_standard.get('quality_score'):.2f})")

            except Exception as e:
                print(f"⚠️ ChatGPT gold standard generation skipped: {e}")

            # Final result (using RAG correction, improved by ChatGPT if applicable)
            final_result = {
                "step": "complete",
                "status": "success",
                "data": {
                    "original_response": str(ai_resp),
                    "corrected_response": str(draft if val.status.value != "rejected" else ai_resp),
                    "confidence": float(val.consensus_score),
                    "final_status": str(val.status.value),
                    "retrieved_documents": [
                        {
                            "user_message": doc.get("user_message", ""),
                            "ai_response": doc.get("ai_response", ""),
                            "similarity_score": float(score)
                        }
                        for doc, score in results[:5]  # Show top 5 retrieved docs
                    ]
                }
            }
            yield f"data: {json.dumps(final_result)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'step': 'error', 'message': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route("/predict", methods=["POST"])
def predict():
    data = request.json
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    user_msg = data.get("user_message")
    ai_resp = data.get("ai_response")

    if not user_msg or not ai_resp:
        return jsonify({"error": "Missing fields"}), 400

    try:
        result = pipeline.process(user_msg, ai_resp)
        return jsonify({
            "hallucination": bool(result.hallucination),
            "hallucination_type": str(result.hallucination_type),
            "bias": bool(result.bias),
            "bias_type": str(result.bias_type),
            "explanation": str(result.explanation),
            "corrected_response": str(result.corrected_response),
            "confidence": float(result.confidence),
            "status": str(result.status)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 AI Detection System Starting...")
    print("="*60)
    print(f"\n📍 Frontend (Vite): http://localhost:5173")
    print(f"📍 API Health:      http://localhost:5174/health")
    print(f"📍 API Predict:     http://localhost:5174/predict")
    print("\n" + "="*60 + "\n")

    app.run(host="0.0.0.0", port=5174, debug=True)
