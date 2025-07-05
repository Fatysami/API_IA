from flask import Blueprint, request, jsonify
from app.utils.ia_router import call_ai
from app.utils.prompt_builders.matching import build_matching_prompt

matching_bp = Blueprint('matching', __name__)

@matching_bp.route("/contextuel", methods=["POST"])
def contextuel_matching():
    data = request.get_json()

    required = ["ia_type", "ia_key", "modele", "prompt", "candidat", "offres"]
    if not all(field in data for field in required):
        return jsonify({"error": "Champs requis manquants"}), 400

    try:
        prompt_final = build_matching_prompt(
            candidat=data["candidat"],
            offres=data["offres"],
            instructions=data["prompt"]
        )

        result = call_ai(
            ia_type=data["ia_type"],
            ia_key=data["ia_key"],
            modele=data["modele"],
            prompt=prompt_final
        )

        return jsonify(eval(result))  # ⚠️ Attention à sécuriser si nécessaire
    except Exception as e:
        return jsonify({"error": "Erreur IA", "details": str(e)}), 500
