from textwrap import dedent

TOPIC = "machine-learning/supervised-learning"

LESSON = {
    "tagline": "Learning from examples that come with the answers 🔑",
    "minutes": 8,
    "level": "beginner",
    "cards": [
        {
            "kind": "hook",
            "emoji": "📬",
            "title": "Your inbox already does this",
            "body": "Gmail learned **spam vs not spam** from millions of emails people had "
            "already marked. That's supervised learning: learn from examples that come with "
            "the right answer, then answer new ones yourself.",
            "figure": "decision_boundary",
        },
        {
            "kind": "tldr",
            "emoji": "⚡",
            "title": "In one line",
            "body": "Inputs **with** answers go in → the model learns a rule → it predicts "
            "answers for inputs it has never seen.",
        },
        {
            "kind": "intuition",
            "emoji": "📝",
            "title": "Studying with an answer key",
            "body": "You try a question, check the key, and adjust. A model does the same "
            "thousands of times: guess, compare with the **label**, fix itself.",
            "figure": "labels_vs_no_labels",
        },
        {
            "kind": "steps",
            "emoji": "🛠️",
            "title": "How it works",
            "body": "Every supervised project follows the same loop.",
            "bullets": [
                "Collect examples: **features** (inputs) + **label** (the answer)",
                "Split them: a **training set** to learn from, a **test set** to check",
                "Train: the model tunes itself to make fewer mistakes",
                "Evaluate on the test set it has never seen",
                "Predict on brand-new data",
            ],
            "figure": "train_test_split",
        },
        {
            "kind": "example",
            "emoji": "🔀",
            "title": "Two flavours",
            "body": "What you predict decides the type of problem.",
            "bullets": [
                "**Classification** → a category: spam or not, fraud or legit, cat or dog",
                "**Regression** → a number: rent, delivery time, tomorrow's temperature",
            ],
        },
        {
            "kind": "math",
            "emoji": "🧮",
            "title": "The model is just a function",
            "body": "Training searches for the f that makes ŷ as close to y as possible on "
            "the training examples.",
            "formula": "ŷ = f(x)",
            "symbols": [
                {"symbol": "x", "meaning": "the features of one example"},
                {"symbol": "y", "meaning": "its true label"},
                {"symbol": "ŷ", "meaning": "the model's prediction"},
                {"symbol": "f", "meaning": "the rule the model learned"},
            ],
        },
        {
            "kind": "example",
            "emoji": "🎭",
            "title": "Memorising isn't learning",
            "body": "Ace the training data but flop on new data? The model memorised noise: "
            "**overfitting**. Too simple to catch the pattern at all? **Underfitting**. You want "
            "the sweet spot in between.",
            "figure": "overfit_underfit",
        },
        {
            "kind": "myth",
            "emoji": "🚩",
            "title": "Myth vs fact",
            "body": "The most common trap in interviews and in real projects.",
            "myth": "Higher accuracy on the training data means a better model.",
            "fact": "Only performance on data the model has never seen counts. 100% training "
            "accuracy is usually a red flag, not a win.",
        },
        {
            "kind": "interview",
            "emoji": "🎤",
            "title": "What interviewers listen for",
            "body": "Keep it crisp and show you know where it goes wrong.",
            "bullets": [
                "A one-line definition plus a real example",
                "Why you hold out a test set",
                "Classification vs regression, with examples",
                "Spotting overfitting from train vs test scores",
            ],
        },
        {
            "kind": "recap",
            "emoji": "✅",
            "title": "Recap",
            "body": "You've got the core idea. Now go break the playground.",
            "bullets": [
                "Supervised = learning from labelled examples",
                "Train on one set, judge on another",
                "Categories → classification, numbers → regression",
                "Train vs test gap reveals overfitting",
            ],
        },
    ],
    "key_terms": [
        {"term": "Feature", "meaning": "An input the model uses, like hours studied."},
        {"term": "Label", "meaning": "The correct answer for an example."},
        {"term": "Training set", "meaning": "Examples the model learns from."},
        {"term": "Test set", "meaning": "Held-out examples used only to measure performance."},
        {"term": "Overfitting", "meaning": "Great on training data, poor on new data."},
        {"term": "Underfitting", "meaning": "Too simple: poor even on training data."},
    ],
}

PLAYGROUND = {
    "widget": "knn_classifier",
    "title": "Teach the machine 🎯",
    "intro": "Each dot is a labelled example. The coloured background shows what the model "
    "(k-nearest neighbours) would predict anywhere on the map. Add points, change k, watch the "
    "boundary react.",
    "tasks": [
        {
            "prompt": "Set k = 1, then add one orange point deep inside the blue area.",
            "hint": "Pick the orange class, then click on the map.",
            "insight": "With k = 1, a single odd point carves out its own island. The model "
            "memorises every example, noise included. That's overfitting.",
        },
        {
            "prompt": "Now slide k up to 15.",
            "hint": "Use the k slider.",
            "insight": "The island disappears. Each prediction is now a vote among 15 "
            "neighbours, so one noisy label can't flip it.",
        },
        {
            "prompt": "Push k to the maximum.",
            "hint": "Drag the slider all the way right.",
            "insight": "The boundary turns into mush and many points land on the wrong side. "
            "Too much smoothing = underfitting.",
        },
        {
            "prompt": "Drag the ⭐ point close to the boundary.",
            "hint": "Grab the star and move it.",
            "insight": "A k-NN prediction is just a vote among the closest labelled examples. "
            "Near the boundary the vote gets close, and that's where uncertainty lives.",
        },
        {
            "prompt": "Switch on test points and compare train vs test accuracy at k = 1 and k = 15.",
            "hint": "Use the 'Show test points' toggle.",
            "insight": "Training accuracy alone lies. A big gap between train and test "
            "accuracy is how you catch overfitting.",
        },
    ],
}

VIDEO = {
    "title": "Supervised learning in 3 minutes",
    "scenes": [
        {
            "title": "The answer key",
            "on_screen": "Learn from examples that have answers",
            "narration": "Every time you mark an email as spam, you're teaching a model. "
            "Supervised learning means learning from examples that already come with the right "
            "answer, the label. Show a model enough of them and it figures out the rule.",
            "figure": "labels_vs_no_labels",
            "seconds": 25,
        },
        {
            "title": "Features and labels",
            "on_screen": "x = features, y = label",
            "narration": "Each example has features, the inputs, and a label, the answer. For "
            "a spam filter the features might be words and links in the email, and the label is "
            "spam or not spam. The model learns a function that maps features to labels.",
            "figure": "decision_boundary",
            "seconds": 30,
        },
        {
            "title": "Train, then test",
            "on_screen": "Never grade on the practice paper",
            "narration": "We split the data. The model learns from the training set, then we "
            "measure it on a test set it has never seen. Grading on the training data is like "
            "grading a student on the exact questions they practised: it tells you nothing.",
            "figure": "train_test_split",
            "seconds": 30,
        },
        {
            "title": "Classification or regression",
            "on_screen": "Category → classification. Number → regression.",
            "narration": "If the answer is a category, like fraud or legit, it's "
            "classification. If it's a number, like rent or delivery time, it's regression. "
            "Same idea, different kind of output.",
            "seconds": 25,
        },
        {
            "title": "Memorising vs learning",
            "on_screen": "Overfit ← sweet spot → underfit",
            "narration": "A model that is too flexible memorises noise and fails on new data. "
            "That's overfitting. One that is too simple misses the pattern entirely. That's "
            "underfitting. Comparing training and test scores tells you which one you have.",
            "figure": "overfit_underfit",
            "seconds": 35,
        },
        {
            "title": "Interview takeaway",
            "on_screen": "Define it, split it, check the gap",
            "narration": "In an interview: define supervised learning in one line with an "
            "example, explain why you hold out a test set, and show you can spot overfitting "
            "from the gap between train and test performance. That's the whole game.",
            "seconds": 25,
        },
    ],
}

PYTHON = {
    "packages": ["numpy", "scikit-learn"],
    "dataset": "400 synthetic app users with two behaviour scores and a label: subscribed (1) "
    "or not (0). The boundary between the groups is curved, generated with make_moons.",
    "steps": [
        {
            "title": "Make labelled data",
            "explanation": "Features X and labels y. Every row is one user and their answer.",
            "code": dedent(
                """\
                import numpy as np
                from sklearn.datasets import make_moons
                from sklearn.model_selection import train_test_split

                # 400 app users described by two (scaled) behaviour scores.
                # Label: 1 = subscribed, 0 = did not. The boundary between them is curved.
                X, y = make_moons(n_samples=400, noise=0.35, random_state=0)
                print("Users:", len(X), "| subscribed:", int(y.sum()), "| not:", int(len(y) - y.sum()))"""
            ),
        },
        {
            "title": "Hold out a test set",
            "explanation": "70% to learn from, 30% kept hidden for an honest score. stratify "
            "keeps the same class balance in both parts.",
            "code": dedent(
                """\
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.3, random_state=42, stratify=y
                )
                print("Train:", len(X_train), "| Test:", len(X_test))"""
            ),
        },
        {
            "title": "Train and predict",
            "explanation": "k-nearest neighbours predicts by letting the 15 closest training "
            "examples vote. fit learns, predict answers, score measures accuracy.",
            "code": dedent(
                """\
                from sklearn.neighbors import KNeighborsClassifier

                model = KNeighborsClassifier(n_neighbors=15)
                model.fit(X_train, y_train)
                new_user = [[0.5, 0.0]]
                print("Prediction for a new user:", "subscribes" if model.predict(new_user)[0] else "does not")
                print("Test accuracy:", round(model.score(X_test, y_test), 2))"""
            ),
        },
        {
            "title": "Spot over- and underfitting",
            "explanation": "k = 1 memorises (perfect train, worse test). k = 151 is too smooth "
            "(both scores drop). The sweet spot sits in between.",
            "code": dedent(
                """\
                for k in (1, 15, 151):
                    knn = KNeighborsClassifier(n_neighbors=k).fit(X_train, y_train)
                    print(f"k={k:>3}  train={knn.score(X_train, y_train):.2f}  test={knn.score(X_test, y_test):.2f}")"""
            ),
        },
    ],
    "expected_output": dedent(
        """\
        Users: 400 | subscribed: 200 | not: 200
        Train: 280 | Test: 120
        Prediction for a new user: subscribes
        Test accuracy: 0.88
        k=  1  train=1.00  test=0.84
        k= 15  train=0.90  test=0.88
        k=151  train=0.81  test=0.79"""
    ),
    "mistakes": [
        "Measuring accuracy on the training data and calling it a result.",
        "Splitting after scaling or feature selection, which leaks test information.",
        "Forgetting stratify on imbalanced data, so the test set has too few of one class.",
        "Picking k (or any setting) by looking at test scores; use a validation set instead.",
    ],
    "applications": [
        "Spam and fraud detection (classification)",
        "Credit scoring and churn prediction",
        "Price, demand and delivery-time forecasting (regression)",
    ],
}

INTERVIEW = {
    "questions": [
        {
            "level": "basic",
            "kind": "conceptual",
            "question": "What is supervised learning? Give an example.",
            "answer": "Learning a mapping from inputs to outputs using examples that already "
            "have the correct output (labels). The model learns from labelled training data and "
            "predicts labels for new data. Example: predicting whether an email is spam from "
            "emails that users have already marked as spam or not spam.",
            "interviewer_wants": "A one-line definition, the word 'labelled', and a concrete "
            "example rather than a textbook phrase.",
            "follow_ups": [
                {
                    "question": "How is it different from unsupervised learning?",
                    "answer": "Unsupervised learning has no labels; it finds structure such as "
                    "clusters or lower-dimensional patterns in the inputs alone.",
                }
            ],
            "origin": "ai_generated",
        },
        {
            "level": "basic",
            "kind": "conceptual",
            "question": "What's the difference between classification and regression?",
            "answer": "Classification predicts a category (spam/not spam, digit 0-9). "
            "Regression predicts a continuous number (price, temperature). Many algorithms come "
            "in both versions, e.g. decision tree classifier vs regressor. They also use "
            "different metrics: accuracy, precision, recall for classification; MSE, MAE, R² "
            "for regression.",
            "interviewer_wants": "Category vs number, an example of each, and awareness that "
            "the evaluation metrics differ.",
            "follow_ups": [
                {
                    "question": "Is predicting a rating from 1 to 5 classification or regression?",
                    "answer": "Either can work. Ordinal targets are often treated as regression "
                    "(then rounded) or as classification; the choice depends on whether the "
                    "distance between classes matters.",
                }
            ],
            "origin": "ai_generated",
        },
        {
            "level": "basic",
            "kind": "practical",
            "question": "Why do we split data into training and test sets?",
            "answer": "To estimate how the model performs on data it has never seen. A model can "
            "memorise the training data, so its training score is optimistic. The test set acts "
            "as new data and must not influence training or model choices.",
            "interviewer_wants": "The idea of generalisation and that the test set must stay "
            "untouched until the end.",
            "follow_ups": [
                {
                    "question": "What's a validation set for, then?",
                    "answer": "For tuning hyperparameters and choosing between models. If you "
                    "tune on the test set, its score is no longer an honest estimate.",
                }
            ],
            "origin": "ai_generated",
        },
        {
            "level": "intermediate",
            "kind": "scenario",
            "question": "Your model has 99% training accuracy and 70% test accuracy. What's "
            "going on and what would you do?",
            "answer": "That gap means overfitting: the model learned noise specific to the "
            "training data. Options: simplify the model (fewer parameters, shallower trees, "
            "larger k in k-NN), add regularisation, get more data, use cross-validation to tune "
            "complexity, remove leaky or noisy features, and for neural networks use dropout or "
            "early stopping.",
            "interviewer_wants": "Naming overfitting from the train/test gap, then several "
            "concrete fixes rather than one.",
            "follow_ups": [
                {
                    "question": "What would low training and low test accuracy suggest?",
                    "answer": "Underfitting: the model is too simple or the features don't "
                    "carry enough signal. Try a more flexible model or better features.",
                }
            ],
            "origin": "ai_generated",
        },
        {
            "level": "intermediate",
            "kind": "conceptual",
            "question": "Explain the bias-variance tradeoff.",
            "answer": "Prediction error can be split into bias (error from overly simple "
            "assumptions), variance (error from sensitivity to the particular training sample) "
            "and irreducible noise. Simple models have high bias and low variance; very flexible "
            "models have low bias and high variance. Good models balance the two, which is what "
            "tuning complexity and regularisation do.",
            "interviewer_wants": "Bias = underfitting, variance = overfitting, and that "
            "reducing one usually increases the other.",
            "follow_ups": [
                {
                    "question": "How does k in k-NN affect bias and variance?",
                    "answer": "Small k: low bias, high variance (jagged boundary). Large k: "
                    "higher bias, lower variance (smooth boundary).",
                }
            ],
            "origin": "ai_generated",
        },
        {
            "level": "intermediate",
            "kind": "coding",
            "question": "How would you train and evaluate a classifier in scikit-learn?",
            "answer": "Split with train_test_split (stratify for classification), create the "
            "model, call fit(X_train, y_train), then evaluate with predict or score on X_test. "
            "Put preprocessing such as scaling inside a Pipeline so it is fitted only on the "
            "training data. Use cross_val_score or GridSearchCV for tuning.",
            "interviewer_wants": "fit/predict/score, a stratified split, and fitting "
            "preprocessing only on training data.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
        {
            "level": "advanced",
            "kind": "scenario",
            "question": "Only 1% of transactions are fraud. Your classifier is 99% accurate. "
            "Is it good?",
            "answer": "Not necessarily: predicting 'not fraud' for everything already gives 99%. "
            "With imbalanced classes, look at precision, recall, F1 and the precision-recall "
            "curve, plus the cost of each error type. Fixes include class weights, resampling, "
            "threshold tuning and stratified splits.",
            "interviewer_wants": "Recognising the accuracy paradox and switching to metrics "
            "and thresholds that match the business cost.",
            "follow_ups": [
                {
                    "question": "Which matters more here, precision or recall?",
                    "answer": "Usually recall (catch fraud), balanced against precision so "
                    "investigators aren't flooded with false alarms. It depends on the costs.",
                }
            ],
            "origin": "ai_generated",
        },
        {
            "level": "advanced",
            "kind": "practical",
            "question": "What is data leakage and how can it creep into a supervised pipeline?",
            "answer": "Leakage is when information that wouldn't be available at prediction time "
            "reaches training, inflating scores. Common causes: scaling or imputing on the full "
            "dataset before splitting, features computed from the target or from the future, and "
            "duplicate rows across train and test. Prevent it by splitting first, fitting "
            "preprocessing inside a pipeline, and respecting time order.",
            "interviewer_wants": "A clear definition and at least two realistic leakage "
            "sources with how to prevent them.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
    ],
    "takeaways": [
        "Supervised learning learns from labelled examples to predict labels for new data.",
        "Category → classification; number → regression.",
        "Judge models only on data they haven't seen; tune on validation, report on test.",
        "A large train/test gap means overfitting; low scores on both mean underfitting.",
        "With imbalanced classes, accuracy alone is misleading.",
    ],
}

QUIZ = {
    "questions": [
        {
            "difficulty": "easy",
            "kind": "concept",
            "prompt": "What makes a learning problem 'supervised'?",
            "options": [
                "The training examples come with correct answers (labels)",
                "A person watches the model while it trains",
                "The data has no labels",
                "The model is retrained every day",
            ],
            "answer": 0,
            "explanation": "Supervised means each training example includes its label, so the "
            "model can compare its guess with the right answer.",
        },
        {
            "difficulty": "easy",
            "kind": "scenario",
            "prompt": "Predicting how many minutes a food delivery will take is…",
            "options": ["Classification", "Regression", "Clustering", "Dimensionality reduction"],
            "answer": 1,
            "explanation": "The output is a number, so it's regression.",
        },
        {
            "difficulty": "easy",
            "kind": "concept",
            "prompt": "Why keep a test set aside?",
            "options": [
                "To make training faster",
                "To estimate performance on data the model hasn't seen",
                "To give the model more examples to learn from",
                "Because the model can't use all the data at once",
            ],
            "answer": 1,
            "explanation": "The test set stands in for future, unseen data, so its score is an "
            "honest estimate.",
        },
        {
            "difficulty": "medium",
            "kind": "scenario",
            "prompt": "Train accuracy 100%, test accuracy 72%. What's the most likely issue?",
            "options": [
                "Underfitting",
                "Overfitting",
                "Too little training time",
                "A perfect model",
            ],
            "answer": 1,
            "explanation": "A big gap between train and test performance is the classic sign of "
            "overfitting.",
        },
        {
            "difficulty": "medium",
            "kind": "concept",
            "prompt": "In k-nearest neighbours, what usually happens as k gets very large?",
            "options": [
                "The boundary gets more jagged",
                "The model memorises the training data",
                "The boundary gets smoother and can underfit",
                "Training accuracy reaches 100%",
            ],
            "answer": 2,
            "explanation": "Averaging over many neighbours smooths the boundary; too much "
            "smoothing ignores real structure.",
        },
        {
            "difficulty": "medium",
            "kind": "code",
            "prompt": "What does this print's number tell you?",
            "code": "model.fit(X_train, y_train)\nprint(model.score(X_test, y_test))",
            "options": [
                "Accuracy on the training data",
                "Accuracy on the held-out test data",
                "The number of correct labels in y_test",
                "The model's loss during training",
            ],
            "answer": 1,
            "explanation": "For classifiers, score returns accuracy on the data you pass in, "
            "here the test set.",
        },
        {
            "difficulty": "hard",
            "kind": "scenario",
            "prompt": "1% of emails are spam. A model that says 'not spam' for every email has "
            "what accuracy?",
            "options": ["1%", "50%", "99%", "It can't be measured"],
            "answer": 2,
            "explanation": "It's right on all 99% non-spam emails. That's why accuracy misleads "
            "on imbalanced data.",
        },
    ]
}

REVISION = {
    "definitions": [
        {
            "term": "Supervised learning",
            "meaning": "Learning a mapping from inputs to outputs using labelled examples.",
        },
        {
            "term": "Feature / label",
            "meaning": "Input variables / the correct answer for an example.",
        },
        {
            "term": "Training / test set",
            "meaning": "Data to learn from / held-out data to measure performance.",
        },
        {
            "term": "Overfitting",
            "meaning": "Fits training data (and its noise) too closely; poor on new data.",
        },
        {
            "term": "Underfitting",
            "meaning": "Too simple to capture the pattern; poor even on training data.",
        },
    ],
    "formulas": [
        {
            "name": "Prediction",
            "expression": "ŷ = f(x)",
            "meaning": "The learned function maps features to a prediction.",
        },
        {
            "name": "Accuracy",
            "expression": "correct predictions / total predictions",
            "meaning": "Share of examples classified correctly.",
        },
    ],
    "comparison": {
        "title": "Classification vs regression",
        "columns": ["", "Classification", "Regression"],
        "rows": [
            ["Output", "A category", "A number"],
            ["Example", "Spam or not", "Delivery time"],
            ["Typical metrics", "Accuracy, precision, recall, F1", "MSE, MAE, R²"],
        ],
    },
    "mistakes": [
        "Reporting training accuracy as the model's performance.",
        "Fitting scalers or encoders before splitting (leakage).",
        "Trusting accuracy on imbalanced classes.",
    ],
    "confusions": [
        {
            "pair": "Validation vs test set",
            "difference": "Validation is for tuning; the test set is touched once, for the final honest score.",
        },
        {
            "pair": "Overfitting vs underfitting",
            "difference": "Big train-test gap vs poor scores on both.",
        },
    ],
    "takeaways": [
        "Labels make it supervised.",
        "Split first, then preprocess and train.",
        "Pick metrics that match the problem and its costs.",
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
