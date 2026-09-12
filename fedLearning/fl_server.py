import logging
import sys
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "ns3-fl-network"))

from flask import Flask, request, jsonify
from fedLearning.utils.fl_server_trainer import FLTrainer
from fedLearning.models import serialize_weights

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[logging.StreamHandler()]
)
logging.getLogger("werkzeug").setLevel(logging.ERROR)

# Create trainer instance
trainer = FLTrainer(project_root=PROJECT_ROOT)
app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    """Check server status and training mode."""
    return jsonify({
        "status": "healthy",
        "mode": trainer.mode,
        "training_mode": "ASYNC" if trainer.is_async else "SYNC"
    })


@app.route("/round_status", methods=["GET"])
def round_status():
    """Get current training progress."""
    if trainer.is_async:
        return jsonify({
            "training_mode": "ASYNC",
            "total_updates": trainer.total_async_updates,
            "training_complete": trainer.training_complete,
        })
    else:
        return jsonify({
            "training_mode": "SYNC",
            "current_round": trainer.current_round,
            "total_rounds": trainer.num_rounds,
            "model_ready": trainer.model_ready,
            "training_complete": trainer.training_complete,
        })


@app.route("/get_model", methods=["GET"])
def get_model():
    """Download current global model."""
    serialized = serialize_weights(trainer.global_model)
    return jsonify({
        "status": "success",
        "round": trainer.current_round if not trainer.is_async else trainer.total_async_updates,
        "version": trainer.global_version,
        "model_weights": serialized,
        "config": {
            "local_epochs": trainer.local_epochs,
            "batch_size": trainer.batch_size,
            "learning_rate": trainer.learning_rate,
        }
    })


@app.route("/submit_update", methods=["POST"])
def submit_update():
    """Handle client model submission (sync or async)."""
    data = request.get_json()
    client_id = data["client_id"]
    
    if trainer.is_async:
        # ASYNC MODE: Process update immediately
        iteration = int(data.get("iteration", 0))
        result, code = trainer.handle_async_update(client_id, iteration, data)
        return jsonify(result), code
    else:
        # SYNC MODE: Store update for aggregation at round boundary
        round_num = int(data.get("round", 0))
        result, code = trainer.handle_sync_update(client_id, round_num, data)
        return jsonify(result), code

def main():
    """Initialize trainer and start training."""
    trainer.setup()
    
    # Start training orchestration based on mode
    if trainer.is_async:
        trainer.logger.info("=" * 60)
        trainer.logger.info("ASYNC MODE: Server ready, waiting for client updates")
        trainer.logger.info("=" * 60)
        trainer.run_fedasync()
    else:
        trainer.logger.info("=" * 60)
        trainer.logger.info("SYNC MODE: Starting synchronous training rounds")
        trainer.logger.info("=" * 60)
        threading.Thread(target=trainer.run_fedsync, daemon=False).start()
    
    # Start Flask server
    trainer.logger.info(f"Starting Flask server on port {trainer.server_port}...")
    app.run(host="0.0.0.0", port=trainer.server_port, threaded=True, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()

