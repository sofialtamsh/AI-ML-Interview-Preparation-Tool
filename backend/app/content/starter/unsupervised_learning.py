from textwrap import dedent

TOPIC = "machine-learning/unsupervised-learning"

LESSON = {
    "tagline": "No answer key? Find the patterns anyway 🧩",
    "minutes": 8,
    "level": "beginner",
    "cards": [
        {
            "kind": "hook",
            "emoji": "🎧",
            "title": "How does Spotify know your vibe?",
            "body": "Nobody labelled your songs 'late-night lo-fi'. The app groups songs and "
            "listeners that behave alike, all on its own. That's **unsupervised learning**.",
            "figure": "clusters",
        },
        {
            "kind": "tldr",
            "emoji": "⚡",
            "title": "In one line",
            "body": "Only inputs, **no labels** → the model discovers structure: groups, "
            "patterns, or a simpler way to describe the data.",
        },
        {
            "kind": "intuition",
            "emoji": "🧺",
            "title": "Sorting a messy drawer",
            "body": "No one tells you the categories, yet you naturally make piles: socks here, "
            "chargers there. Clustering does the same with data points that sit close together.",
            "figure": "labels_vs_no_labels",
        },
        {
            "kind": "example",
            "emoji": "🧭",
            "title": "What it's used for",
            "body": "Three jobs come up again and again.",
            "bullets": [
                "**Clustering**: customer segments, similar songs, topic groups",
                "**Dimensionality reduction** (PCA): squash 100 features into a few that matter",
                "**Anomaly detection**: flag the transaction that fits no pattern",
            ],
        },
        {
            "kind": "steps",
            "emoji": "🔁",
            "title": "K-means in 4 moves",
            "body": "The most asked-about clustering algorithm repeats two simple steps.",
            "bullets": [
                "Pick k and drop k centroids (k-means++ spreads them out smartly)",
                "**Assign**: every point joins its nearest centroid",
                "**Update**: move each centroid to the average of its points",
                "Repeat until nothing changes",
            ],
            "figure": "clusters",
        },
        {
            "kind": "math",
            "emoji": "🧮",
            "title": "What k-means minimises",
            "body": "Inertia: the total squared distance from each point to its own centroid. "
            "Smaller means tighter clusters.",
            "formula": "J = Σ ‖xᵢ − μ_c(i)‖²",
            "symbols": [
                {"symbol": "xᵢ", "meaning": "a data point"},
                {"symbol": "μ_c(i)", "meaning": "the centroid of the cluster xᵢ belongs to"},
                {"symbol": "J", "meaning": "inertia (within-cluster sum of squares)"},
            ],
        },
        {
            "kind": "example",
            "emoji": "📐",
            "title": "So how many clusters?",
            "body": "Inertia always drops as k grows, so don't just minimise it. Look for the "
            "**elbow** where gains flatten, and check the **silhouette** score (closer to 1 = "
            "better separated).",
        },
        {
            "kind": "myth",
            "emoji": "🚩",
            "title": "Myth vs fact",
            "body": "Clusters are a lens, not the truth.",
            "myth": "The clusters k-means finds are the real, natural groups in the data.",
            "fact": "K-means always returns k groups, even in random noise. It assumes round, "
            "similar-sized clusters, and it's sensitive to feature scaling.",
        },
        {
            "kind": "interview",
            "emoji": "🎤",
            "title": "What interviewers listen for",
            "body": "Show you know the algorithm and its limits.",
            "bullets": [
                "Supervised vs unsupervised in one line",
                "The assign → update loop of k-means",
                "Choosing k: elbow + silhouette",
                "Why you scale features first",
            ],
        },
        {
            "kind": "recap",
            "emoji": "✅",
            "title": "Recap",
            "body": "Now go watch clusters form in the playground.",
            "bullets": [
                "Unsupervised = no labels, find structure",
                "K-means: assign to nearest centroid, move centroids, repeat",
                "Pick k with the elbow and silhouette",
                "Scale features; expect round clusters",
            ],
        },
    ],
    "key_terms": [
        {"term": "Cluster", "meaning": "A group of points that are similar to each other."},
        {"term": "Centroid", "meaning": "The average point of a cluster."},
        {"term": "Inertia", "meaning": "Total squared distance of points to their centroid."},
        {"term": "Elbow method", "meaning": "Pick k where adding clusters stops helping much."},
        {"term": "Silhouette score", "meaning": "From −1 to 1: how well separated clusters are."},
    ],
}

PLAYGROUND = {
    "widget": "kmeans",
    "title": "Watch clusters form 🫧",
    "intro": "The points have no labels. Pick k, then step through k-means: points join their "
    "nearest centroid, centroids move to the middle of their group, repeat.",
    "tasks": [
        {
            "prompt": "Keep k = 3 and press Step a few times.",
            "hint": "Each press does one assign or one update.",
            "insight": "Centroids slide toward the centre of their groups and stop once no "
            "point changes cluster. That's convergence.",
        },
        {
            "prompt": "Set k = 6 on data with 3 visible blobs.",
            "hint": "Move the k slider, then Run.",
            "insight": "K-means happily splits real groups to give you 6. It always returns "
            "exactly k clusters, whether or not they make sense.",
        },
        {
            "prompt": "Open the elbow chart and find where the curve bends.",
            "hint": "Look for where the line stops dropping steeply.",
            "insight": "Inertia always shrinks as k grows. The bend (the elbow) is where "
            "extra clusters stop buying much.",
        },
        {
            "prompt": "Press New starting points a few times with k = 4.",
            "hint": "Same data, different random centroids.",
            "insight": "Different starts can end in different answers. That's why libraries "
            "run k-means several times (n_init) and keep the best.",
        },
    ],
}

VIDEO = {
    "title": "Unsupervised learning & k-means in 3 minutes",
    "scenes": [
        {
            "title": "No answers given",
            "on_screen": "No labels. Just patterns.",
            "narration": "In supervised learning every example comes with an answer. Here there "
            "are none. Unsupervised learning looks only at the inputs and finds structure "
            "nobody pointed out, like groups of similar customers or songs.",
            "figure": "labels_vs_no_labels",
            "seconds": 25,
        },
        {
            "title": "Three big jobs",
            "on_screen": "Cluster · Compress · Catch outliers",
            "narration": "Most unsupervised work is one of three jobs: clustering similar items, "
            "reducing many features to a few with methods like PCA, or spotting anomalies that "
            "fit no pattern, like a suspicious payment.",
            "seconds": 25,
        },
        {
            "title": "K-means, step by step",
            "on_screen": "Assign → update → repeat",
            "narration": "K-means starts with k centroids. Each point joins the nearest one. "
            "Then every centroid moves to the average of its points. Assign, update, repeat, "
            "until nothing changes. Simple, fast, and everywhere.",
            "figure": "clusters",
            "seconds": 35,
        },
        {
            "title": "What it optimises",
            "on_screen": "Minimise inertia",
            "narration": "Behind the scenes, k-means minimises inertia: the total squared "
            "distance from each point to its centroid. Each assign step and each update step "
            "can only lower it, which is why the algorithm settles down.",
            "seconds": 30,
        },
        {
            "title": "Choosing k",
            "on_screen": "Elbow + silhouette",
            "narration": "Inertia always falls as you add clusters, so you can't just minimise "
            "it. Plot it against k and look for the elbow, then check the silhouette score, "
            "which rewards tight, well separated clusters.",
            "seconds": 30,
        },
        {
            "title": "Interview takeaway",
            "on_screen": "Know the loop, know the limits",
            "narration": "Explain the assign and update loop, how you'd pick k, and the "
            "catches: scale your features, expect round clusters, and remember k-means returns "
            "k groups even when the data has none.",
            "seconds": 25,
        },
    ],
}

PYTHON = {
    "packages": ["numpy", "scikit-learn"],
    "dataset": "300 synthetic shoppers with two features, generated with make_blobs. The true "
    "group labels exist but we deliberately throw them away.",
    "steps": [
        {
            "title": "Unlabelled data",
            "explanation": "make_blobs also returns labels; the underscore throws them away so "
            "the model only ever sees X.",
            "code": dedent(
                """\
                import numpy as np
                from sklearn.datasets import make_blobs

                # 300 shoppers described by two features. We never use the "true group" labels.
                X, _ = make_blobs(n_samples=300, centers=3, cluster_std=0.9, random_state=7)
                print("Shoppers:", X.shape[0], "| features:", X.shape[1])"""
            ),
        },
        {
            "title": "Run k-means",
            "explanation": "n_init=10 runs ten different starts and keeps the best; "
            "random_state makes it repeatable.",
            "code": dedent(
                """\
                from sklearn.cluster import KMeans

                kmeans = KMeans(n_clusters=3, n_init=10, random_state=0)
                labels = kmeans.fit_predict(X)
                sizes = np.bincount(labels)
                print("Cluster sizes:", sorted(sizes.tolist()))
                print("Inertia (k=3):", round(kmeans.inertia_, 1))"""
            ),
        },
        {
            "title": "The elbow",
            "explanation": "Inertia for k = 1…6. Watch the huge drops stop after k = 3.",
            "code": dedent(
                """\
                for k in range(1, 7):
                    inertia = KMeans(n_clusters=k, n_init=10, random_state=0).fit(X).inertia_
                    print(f"k={k}  inertia={inertia:8.1f}")"""
            ),
        },
        {
            "title": "Silhouette check",
            "explanation": "Higher is better separated. It peaks at the k the data supports.",
            "code": dedent(
                """\
                from sklearn.metrics import silhouette_score

                for k in (2, 3, 4):
                    labels_k = KMeans(n_clusters=k, n_init=10, random_state=0).fit_predict(X)
                    print(f"k={k}  silhouette={silhouette_score(X, labels_k):.2f}")"""
            ),
        },
    ],
    "expected_output": dedent(
        """\
        Shoppers: 300 | features: 2
        Cluster sizes: [100, 100, 100]
        Inertia (k=3): 464.5
        k=1  inertia= 18552.6
        k=2  inertia=  3189.5
        k=3  inertia=   464.5
        k=4  inertia=   406.3
        k=5  inertia=   352.2
        k=6  inertia=   303.1
        k=2  silhouette=0.75
        k=3  silhouette=0.81
        k=4  silhouette=0.66"""
    ),
    "mistakes": [
        "Not scaling features, so one large-valued feature dominates the distances.",
        "Picking k by the lowest inertia (it always prefers more clusters).",
        "Running k-means once and trusting a possibly bad random start.",
        "Using k-means on long, curved or very unequal clusters (try DBSCAN or GMMs).",
    ],
    "applications": [
        "Customer segmentation for marketing",
        "Grouping similar products, songs or articles",
        "Compressing colours in an image (colour quantisation)",
    ],
}

INTERVIEW = {
    "questions": [
        {
            "level": "basic",
            "kind": "conceptual",
            "question": "What is unsupervised learning? How does it differ from supervised learning?",
            "answer": "Unsupervised learning works with unlabelled data and finds structure in "
            "the inputs alone, such as clusters, lower-dimensional representations or anomalies. "
            "Supervised learning needs labels and learns to predict them. Example: segmenting "
            "customers by behaviour without any predefined segments.",
            "interviewer_wants": "The 'no labels' point, a task type (clustering, reduction, "
            "anomaly detection) and a real example.",
            "follow_ups": [
                {
                    "question": "How do you evaluate a model when there are no labels?",
                    "answer": "With internal metrics (inertia, silhouette), stability across "
                    "runs, and whether the result is useful downstream or makes sense to domain "
                    "experts.",
                }
            ],
            "origin": "ai_generated",
        },
        {
            "level": "basic",
            "kind": "conceptual",
            "question": "Walk me through the k-means algorithm.",
            "answer": "Choose k and initialise k centroids (usually with k-means++). Repeat: "
            "assign each point to its nearest centroid, then move each centroid to the mean of "
            "its assigned points. Stop when assignments no longer change or a maximum number of "
            "iterations is reached. It minimises the within-cluster sum of squared distances.",
            "interviewer_wants": "The two alternating steps, the stopping condition, and what "
            "objective it minimises.",
            "follow_ups": [
                {
                    "question": "Is k-means guaranteed to find the best clustering?",
                    "answer": "No. It converges to a local minimum that depends on "
                    "initialisation, which is why it's run several times (n_init).",
                }
            ],
            "origin": "ai_generated",
        },
        {
            "level": "intermediate",
            "kind": "practical",
            "question": "How do you choose the number of clusters k?",
            "answer": "Plot inertia against k and look for the elbow where improvements "
            "flatten; compute the silhouette score for several k and prefer higher values; use "
            "the gap statistic; and above all check whether the clusters are interpretable and "
            "useful for the business question.",
            "interviewer_wants": "More than one method, and the note that inertia always "
            "decreases with k.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
        {
            "level": "intermediate",
            "kind": "scenario",
            "question": "One feature is annual income in rupees, another is age. You run k-means "
            "and the clusters only split by income. Why?",
            "answer": "K-means uses Euclidean distance, and income's scale is far larger than "
            "age's, so it dominates every distance. Standardise or normalise features (e.g. "
            "StandardScaler) before clustering so each contributes fairly.",
            "interviewer_wants": "Distance-based algorithms need feature scaling, and why.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
        {
            "level": "intermediate",
            "kind": "math",
            "question": "What does a silhouette score of 0.8 vs 0.1 tell you?",
            "answer": "The silhouette compares each point's average distance to its own cluster "
            "(a) with its distance to the nearest other cluster (b): s = (b − a) / max(a, b). "
            "Near 1 means well separated clusters (0.8 is strong); near 0 means points sit on "
            "the borders between clusters (0.1 is weak); negative suggests misassignment.",
            "interviewer_wants": "What the score compares, its range, and how to read values.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
        {
            "level": "advanced",
            "kind": "conceptual",
            "question": "When does k-means fail, and what would you use instead?",
            "answer": "It assumes roughly spherical, similarly sized clusters, so it struggles "
            "with elongated or curved shapes, very different densities, and outliers (which "
            "drag centroids). Alternatives: DBSCAN or HDBSCAN for arbitrary shapes and noise, "
            "Gaussian Mixture Models for elliptical clusters with soft assignments, and "
            "hierarchical clustering when you want a dendrogram.",
            "interviewer_wants": "Concrete failure cases and matching alternatives.",
            "follow_ups": [
                {
                    "question": "What does DBSCAN need instead of k?",
                    "answer": "A neighbourhood radius (eps) and a minimum number of points; it "
                    "finds dense regions and marks sparse points as noise.",
                }
            ],
            "origin": "ai_generated",
        },
        {
            "level": "advanced",
            "kind": "coding",
            "question": "How would you cluster customers in scikit-learn so the result is "
            "reproducible and fair to every feature?",
            "answer": "Build a Pipeline with StandardScaler followed by KMeans(n_clusters=k, "
            "n_init=10, random_state=0). Fit on the customer features, read labels_ or call "
            "predict for new customers, and evaluate k with inertia and silhouette_score.",
            "interviewer_wants": "Scaling inside a pipeline, n_init, random_state, and an "
            "evaluation step.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
    ],
    "takeaways": [
        "Unsupervised learning finds structure without labels.",
        "K-means alternates assign and update steps to minimise inertia.",
        "Choose k with the elbow, silhouette and common sense.",
        "Scale features; k-means prefers round, similar-sized clusters.",
    ],
}

QUIZ = {
    "questions": [
        {
            "difficulty": "easy",
            "kind": "concept",
            "prompt": "What does unsupervised learning work with?",
            "options": [
                "Examples with labels",
                "Inputs without labels",
                "Only images",
                "A reward signal from a game",
            ],
            "answer": 1,
            "explanation": "No labels: the model finds structure in the inputs themselves.",
        },
        {
            "difficulty": "easy",
            "kind": "scenario",
            "prompt": "Which task is unsupervised?",
            "options": [
                "Predicting house prices from past sales",
                "Grouping customers by shopping behaviour",
                "Detecting spam from labelled emails",
                "Recognising handwritten digits from labelled images",
            ],
            "answer": 1,
            "explanation": "Grouping without predefined categories is clustering.",
        },
        {
            "difficulty": "medium",
            "kind": "concept",
            "prompt": "In k-means, what happens in the update step?",
            "options": [
                "Each point moves toward the nearest centroid",
                "Each centroid moves to the mean of its assigned points",
                "k increases by one",
                "Outliers are removed",
            ],
            "answer": 1,
            "explanation": "Assign points to the nearest centroid, then move centroids to the "
            "average of their points.",
        },
        {
            "difficulty": "medium",
            "kind": "concept",
            "prompt": "Why can't you choose k simply by picking the lowest inertia?",
            "options": [
                "Inertia always decreases as k grows",
                "Inertia is always zero",
                "Inertia only works for k = 2",
                "Lower inertia means worse clusters",
            ],
            "answer": 0,
            "explanation": "More clusters always reduce inertia (k = number of points gives 0), "
            "so you look for the elbow instead.",
        },
        {
            "difficulty": "medium",
            "kind": "scenario",
            "prompt": "Features are salary (₹) and age. Clusters split only by salary. Fix?",
            "options": [
                "Use more clusters",
                "Scale the features before clustering",
                "Remove the age feature",
                "Run fewer iterations",
            ],
            "answer": 1,
            "explanation": "Distances are dominated by the large-scale feature until you "
            "standardise.",
        },
        {
            "difficulty": "hard",
            "kind": "math",
            "prompt": "A silhouette score close to 0 for most points suggests…",
            "options": [
                "Very well separated clusters",
                "Points lie near the boundaries between clusters",
                "The data has no outliers",
                "k-means converged perfectly",
            ],
            "answer": 1,
            "explanation": "Near 0 means a point is about as close to another cluster as to its "
            "own.",
        },
        {
            "difficulty": "hard",
            "kind": "scenario",
            "prompt": "Your data forms two interlocking crescent shapes. Best choice?",
            "options": ["k-means with k = 2", "DBSCAN", "Linear regression", "k-means with k = 10"],
            "answer": 1,
            "explanation": "Density-based clustering follows arbitrary shapes; k-means assumes "
            "round clusters.",
        },
    ]
}

REVISION = {
    "definitions": [
        {"term": "Unsupervised learning", "meaning": "Finding structure in data without labels."},
        {"term": "Clustering", "meaning": "Grouping similar points together."},
        {"term": "Centroid", "meaning": "The mean of the points in a cluster."},
        {"term": "Inertia", "meaning": "Sum of squared distances from points to their centroid."},
        {"term": "Silhouette", "meaning": "(b − a) / max(a, b); near 1 = well separated."},
    ],
    "formulas": [
        {
            "name": "K-means objective",
            "expression": "J = Σ ‖xᵢ − μ_c(i)‖²",
            "meaning": "Total squared distance to assigned centroids.",
        },
        {
            "name": "Silhouette",
            "expression": "s = (b − a) / max(a, b)",
            "meaning": "a: mean distance within the cluster; b: to the nearest other cluster.",
        },
    ],
    "comparison": {
        "title": "Supervised vs unsupervised",
        "columns": ["", "Supervised", "Unsupervised"],
        "rows": [
            ["Labels", "Yes", "No"],
            ["Goal", "Predict the label", "Find structure"],
            ["Examples", "Spam filter, price prediction", "Segments, PCA, anomalies"],
            ["Evaluation", "Compare with true labels", "Silhouette, inertia, usefulness"],
        ],
    },
    "mistakes": [
        "Clustering unscaled features.",
        "Choosing k by minimum inertia.",
        "Assuming clusters are 'real' groups without checking.",
    ],
    "confusions": [
        {
            "pair": "k-means vs k-NN",
            "difference": "k-means clusters unlabelled data into k groups; k-NN classifies using k labelled neighbours.",
        },
    ],
    "takeaways": [
        "No labels → unsupervised.",
        "K-means: assign, update, repeat.",
        "Pick k with the elbow and silhouette.",
    ],
}

CONTENT = {
    "lesson": LESSON,
    "playground": PLAYGROUND,
    "video": VIDEO,
    "python": PYTHON,
    "interview": INTERVIEW,
    "quiz": QUIZ,
    "revision": REVISION,
}
