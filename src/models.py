"""Model loading + fine-tuning wrappers (BERTurk, ConvBERTurk).

STUB -- deliberately not implemented.

Briefing S2/S4: the training script is written once, verified, and kept in
sync with the execution-phase conversation that produces it. Inventing a
plausible-looking Trainer setup here would create a second, unverified source
of truth that a notebook might import by accident.

When implemented, this module must:
  * seed python/numpy/torch with config.SEED (42) and record it in the result
  * use config.MODEL_BASELINE then config.MODEL_SECOND, max_len=config.MAX_LEN
  * checkpoint every epoch (free Kaggle/Colab sessions drop mid-run) and
    document the resume path
  * write results to a step-named JSON in results/ that a rerun cannot clobber
"""


def load_model(*args, **kwargs):
    raise NotImplementedError(
        "src/models.py is a stub. Do not fill it in with invented training code -- "
        "it gets written when the Day 2 script is specified. See module docstring."
    )


def train(*args, **kwargs):
    raise NotImplementedError(
        "src/models.py is a stub. Do not fill it in with invented training code -- "
        "it gets written when the Day 2 script is specified. See module docstring."
    )
