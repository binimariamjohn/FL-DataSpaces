import sys
import numpy as np
from typing import Dict

# Fedavg for synchornous aggregation
def fedavg(updates: Dict, model, **kwargs) -> bool:   
    if not updates:
        return False

    updates_list = list(updates.values())
    total = sum(u["num_samples"] for u in updates_list)
    if total <= 0:
        return False

    new_weights = [np.zeros_like(w) for w in model.get_weights()]
    for u in updates_list:
        frac = u["num_samples"] / total
        for i, w in enumerate(u["weights"]):
            new_weights[i] += w * frac

    model.set_weights(new_weights)

    _log(f"FedAvg: {len(updates)} clients, total_samples={total}")
    return True

#fedasync for asynchronous aggregation
def fedavg_async(updates: Dict, model, alpha_init: float = 0.6,
                 staleness_fn: str = 'polynomial', **kwargs) -> bool:
    if not updates:
        return False

    current_weights = model.get_weights()
    updates_list = list(updates.items())

    total_samples = sum(u[1]["num_samples"] for u in updates_list)
    if total_samples <= 0:
        return False

    target_weights = [np.zeros_like(w) for w in current_weights]
    avg_staleness = 0.0
    details = []

    for client_id, u in updates_list:
        share = u["num_samples"] / total_samples
        staleness = u.get("staleness", 0)
        avg_staleness += staleness * share
        details.append(f"C{client_id}(n={u['num_samples']}, s={staleness}, share={share:.4f})")

        for i, w in enumerate(u["weights"]):
            target_weights[i] += w * share

    # Compute staleness-dependent learning rate
    if staleness_fn == 'constant':
        s_t = 1.0
    elif staleness_fn == 'polynomial':
        s_t = (avg_staleness + 1) ** (-0.5)
    elif staleness_fn == 'hinge':
        s_t = 1.0 if avg_staleness <= 4 else 1.0 / (10 * (avg_staleness - 4) + 1)
    else:
        s_t = 1.0

    alpha_t = alpha_init * s_t
    new_weights = [
        (1 - alpha_t) * curr + alpha_t * target
        for curr, target in zip(current_weights, target_weights)
    ]

    model.set_weights(new_weights)

    _log(f"FedAsync: {' | '.join(details)} | "
         f"avg_staleness={avg_staleness:.2f} | s_t={s_t:.4f} | alpha_t={alpha_t:.4f}")
    return True


def _log(msg: str):  
    if hasattr(sys, '_fedasync_logger'):
        sys._fedasync_logger.info(msg)

