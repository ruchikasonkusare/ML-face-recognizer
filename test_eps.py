# test_eps.py
from cors.clusterer import load_fingerprints, find_best_eps

fingerprints = load_fingerprints()
find_best_eps(fingerprints)