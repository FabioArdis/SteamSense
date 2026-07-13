"""
k-means clustering over the dataset population's feature vectors.

k=2 was chosen via silhouette score and corroborated by inertia (there was no clear "elbow" and smooth decline) and
PCA visualization (one continuous blob). based on the centroid averages, i interpreted the two clusters as such:
- cluster 0 (~849 users): narrow genre/developer entropy, uneven playtime distribution. "Focused Loyalists"
- cluster 1 (~1903 users): wide genre/developer variety, more evenly distributed playtime. "Broad Explorers"

split is driven most entirely by genre_entropy/developer_entropy. indeed, median_playtime and average_review_scores are
nearly identical across both clusters.

there's a limitation worth mentioning: average_game_age_norm is min-max normalized against the population observed at
fit time. if the current population changes, the min/max shifts and every previously normalized value becomes stale.
should be acceptable for now, as I haven't personally found a better dataset.
"""
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

import pandas as pd

# we have to make sure that every new data point has these exact columns in this exact order.
FEATURE_COLUMNS = [
    "median_playtime",
    "std_playtime",
    "genre_entropy",
    "developer_entropy",
    "average_game_age_norm",
    "average_review_score",
]

def build_clustering_matrix(complete_features):
    # we're going to apply min-max normalization or the age numbers will dominate the vector.
    min_age = complete_features["average_game_age"].min()
    max_age = complete_features["average_game_age"].max()
    complete_features = complete_features.copy()

    # (x - min) / (max - min)
    complete_features["average_game_age_norm"] = (
        (complete_features["average_game_age"] - min_age) / (max_age - min_age)
    )

    return complete_features[FEATURE_COLUMNS], min_age, max_age

def build_live_vector(live_features: dict, min_age: float, max_age: float) -> pd.DataFrame:
    # since we don't normalize the user's game age earlier, we do it now. if we don't, a single live user would have
    # min == max, leading to a 0/0 division.
    age_norm = (live_features["average_game_age"] - min_age) / (max_age - min_age)

    vector = pd.DataFrame([{
        "median_playtime": live_features["median"],
        "std_playtime": live_features["std"],
        "genre_entropy": live_features["genre_entropy"],
        "developer_entropy": live_features["developer_entropy"],
        "average_game_age_norm": age_norm,
        "average_review_score": live_features["average_review_score"],
    }])[FEATURE_COLUMNS] # this forces the columns to be in the exact order of FEATURE_COLUMNS. just to be safe

    return vector

def find_best_k(matrix, k_range=range(2, 11)):
    scores = {}

    for k in k_range:
        # random_state = 41 because we all love 41 <3
        # but seriously, it's because we need determinism between runs. n_init = 10 means the algo runs 10 different
        # times with random starting points and picks the best one.
        kmeans = KMeans(n_clusters=k, random_state=41, n_init=10)

        # fit_predict does the math and groups the rows into clusters in one step.
        labels = kmeans.fit_predict(matrix)

        # then, we finally give a score to the clusters.
        score = silhouette_score(matrix, labels)
        scores[k] = score
        print(f"k={k}: silhouette score = {score:.4f}")
    return scores

def assign_to_cluster(kmeans, vector: pd.DataFrame) -> int:
    # predicting which cluster our user belongs to.
    # we only care about the first element in the array.
    return kmeans.predict(vector)[0]

def explain_cluster_assignment(matrix, vector: pd.DataFrame, cluster_label: int) -> pd.DataFrame:
    # grab the average stats for whichever group the user landed in.
    cluster_mean = matrix[matrix["cluster"] == cluster_label][FEATURE_COLUMNS].mean()

    comparison = pd.DataFrame({
        "your_value": vector.iloc[0],
        "cluster_average": cluster_mean,
    })

    # calculate the difference to show the user how they stack up against their peers.
    comparison["difference"] = comparison["your_value"] - comparison["cluster_average"]
    return comparison