"""Machine-learning adapters.

Houses the scikit-learn implementation of the ``RiskAssessor`` port, the shared
``FeatureBuilder`` (used by both training and serving to avoid train/serve skew),
and model-artifact loading with ``model_version`` tracking. Built in Phase 5;
the package exists now to anchor the architecture.
"""
