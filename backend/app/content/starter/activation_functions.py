from textwrap import dedent

TOPIC = "deep-learning/activation-functions"

LESSON = {
    "tagline": "The little bend that makes deep learning work 〰️",
    "minutes": 8,
    "level": "beginner",
    "cards": [
        {
            "kind": "hook",
            "emoji": "🎛️",
            "title": "Straight lines can't draw faces",
            "body": "Stack a hundred linear layers and you still get… a straight line. "
            "**Activation functions** add the bends that let networks recognise faces, voices "
            "and text.",
            "figure": "activation_curves",
        },
        {
            "kind": "tldr",
            "emoji": "⚡",
            "title": "In one line",
            "body": "After each weighted sum, an activation squashes or clips the value. That "
            "non-linearity is what lets layers learn complex patterns.",
        },
        {
            "kind": "example",
            "emoji": "📈",
            "title": "Meet the line-up",
            "body": "The ones you'll be asked about.",
            "bullets": [
                "**Sigmoid**: 0 to 1, great for a yes/no probability",
                "**Tanh**: −1 to 1, zero-centred",
                "**ReLU**: max(0, z), the default for hidden layers",
                "**Leaky ReLU / GELU**: ReLU's smoother, never-fully-dead cousins",
                "**Softmax**: turns scores into probabilities that sum to 1",
            ],
            "figure": "activation_curves",
        },
        {
            "kind": "math",
            "emoji": "🧮",
            "title": "The two classics",
            "body": "Sigmoid squashes everything into (0, 1). ReLU keeps positives and zeroes "
            "out negatives: dirt cheap to compute.",
            "formula": "σ(z) = 1 / (1 + e⁻ᶻ)    ReLU(z) = max(0, z)",
            "symbols": [
                {"symbol": "z", "meaning": "the neuron's weighted sum w·x + b"},
                {"symbol": "e", "meaning": "Euler's number, about 2.718"},
            ],
        },
        {
            "kind": "intuition",
            "emoji": "🫥",
            "title": "The vanishing gradient",
            "body": "Sigmoid's slope is at most **0.25**. Backprop multiplies one slope per "
            "layer, so 10 layers can shrink the signal by about a million times. Early layers "
            "barely learn.",
        },
        {
            "kind": "example",
            "emoji": "💡",
            "title": "Why ReLU won",
            "body": "ReLU's slope is exactly 1 for positive inputs, so gradients pass through "
            "deep stacks without shrinking. It's also just a max, so it's fast.",
        },
        {
            "kind": "steps",
            "emoji": "🧭",
            "title": "Which one where?",
            "body": "A cheat code for real projects.",
            "bullets": [
                "Hidden layers → ReLU (or GELU in transformers)",
                "Binary output → sigmoid",
                "Multi-class output → softmax",
                "Regression output → no activation (linear)",
            ],
        },
        {
            "kind": "myth",
            "emoji": "🚩",
            "title": "Myth vs fact",
            "body": "ReLU has one famous failure mode.",
            "myth": "ReLU neurons can always recover during training.",
            "fact": "If a ReLU neuron's input stays negative, its gradient is 0 and it may never "
            "update again: a **dying ReLU**. Leaky ReLU keeps a small slope to prevent this.",
        },
        {
            "kind": "interview",
            "emoji": "🎤",
            "title": "What interviewers listen for",
            "body": "Trade-offs, not definitions.",
            "bullets": [
                "Why non-linearity is needed at all",
                "Vanishing gradients with sigmoid/tanh",
                "Dying ReLU and how Leaky ReLU helps",
                "Matching output activations to the task",
            ],
        },
        {
            "kind": "recap",
            "emoji": "✅",
            "title": "Recap",
            "body": "Go compare the curves and their slopes in the playground.",
            "bullets": [
                "Activations add non-linearity",
                "Sigmoid/tanh saturate → vanishing gradients",
                "ReLU is the hidden-layer default",
                "Output activation depends on the task",
            ],
        },
    ],
    "key_terms": [
        {
            "term": "Activation function",
            "meaning": "A non-linear function applied to a neuron's sum.",
        },
        {"term": "Saturation", "meaning": "Flat regions where the slope is near zero."},
        {
            "term": "Vanishing gradient",
            "meaning": "Gradients shrinking as they flow back through layers.",
        },
        {"term": "Dying ReLU", "meaning": "A ReLU neuron stuck outputting 0 with zero gradient."},
        {"term": "Softmax", "meaning": "Turns a vector of scores into probabilities summing to 1."},
    ],
}

PLAYGROUND = {
    "widget": "activation_functions",
    "title": "Bend the line 〰️",
    "intro": "Compare activation functions and their slopes (derivatives). Move z to see the "
    "output and the gradient, then stack layers to watch gradients vanish.",
    "tasks": [
        {
            "prompt": "Pick Sigmoid and slide z to 6.",
            "hint": "Use the z slider.",
            "insight": "The output is stuck near 1 and the slope is almost 0. Saturated neurons "
            "barely pass any gradient back.",
        },
        {
            "prompt": "Switch to ReLU and slide z from −3 to 3.",
            "hint": "Watch the slope readout.",
            "insight": "The slope is 0 for negatives and exactly 1 for positives: no shrinking "
            "for active neurons.",
        },
        {
            "prompt": "Set layers to 10 and compare Sigmoid with ReLU in the gradient bar.",
            "hint": "Use the layers slider under the chart.",
            "insight": "Sigmoid's gradient shrinks to about one millionth (0.25¹⁰). That's the "
            "vanishing gradient problem in one picture.",
        },
        {
            "prompt": "Compare Leaky ReLU and ReLU at z = −2.",
            "hint": "Switch between them with z fixed.",
            "insight": "Leaky ReLU keeps a small slope for negatives, so the neuron can still "
            "learn instead of dying.",
        },
    ],
}

VIDEO = {
    "title": "Activation functions in 3 minutes",
    "scenes": [
        {
            "title": "The missing bend",
            "on_screen": "No activation = still a straight line",
            "narration": "Stack as many linear layers as you like and you still get a straight "
            "line. Activation functions add a bend after every layer, and those bends are what "
            "let neural networks learn real-world patterns.",
            "figure": "activation_curves",
            "seconds": 25,
        },
        {
            "title": "Sigmoid and tanh",
            "on_screen": "Squash into (0, 1) or (−1, 1)",
            "narration": "Sigmoid squashes any number into the range zero to one, perfect for a "
            "probability. Tanh does the same between minus one and one, and it's centred on "
            "zero, which often trains a little better in hidden layers.",
            "seconds": 30,
        },
        {
            "title": "The vanishing gradient",
            "on_screen": "0.25 × 0.25 × 0.25 …",
            "narration": "Here's the catch. Sigmoid's slope is never more than a quarter. "
            "Backpropagation multiplies one slope per layer, so through ten layers the gradient "
            "can shrink a million times. The early layers stop learning.",
            "seconds": 30,
        },
        {
            "title": "Enter ReLU",
            "on_screen": "ReLU(z) = max(0, z)",
            "narration": "ReLU keeps positive values and zeroes out negatives. Its slope is "
            "exactly one when active, so gradients flow through deep networks. It's also just "
            "a max, so it's fast. That's why it's the default for hidden layers.",
            "figure": "activation_curves",
            "seconds": 35,
        },
        {
            "title": "Dying ReLU and friends",
            "on_screen": "Leaky ReLU · GELU",
            "narration": "If a ReLU neuron only ever sees negative inputs, it outputs zero, "
            "gets zero gradient and can die. Leaky ReLU keeps a small slope for negatives. "
            "GELU, a smooth curve, is the favourite inside transformers.",
            "seconds": 30,
        },
        {
            "title": "Interview takeaway",
            "on_screen": "Hidden: ReLU · Binary: sigmoid · Classes: softmax",
            "narration": "Remember the map: ReLU or GELU in hidden layers, sigmoid for a binary "
            "output, softmax for multiple classes, and no activation for regression. Then "
            "explain vanishing gradients and dying ReLUs, and you're set.",
            "seconds": 25,
        },
    ],
}

PYTHON = {
    "packages": ["numpy"],
    "dataset": "Five sample inputs z = −3, −1, 0, 1, 3 and a small vector of class scores for "
    "softmax. No dataset needed: we compare the functions directly.",
    "steps": [
        {
            "title": "Define the activations",
            "explanation": "Each is one line of NumPy. GELU uses the common tanh approximation.",
            "code": dedent(
                """\
                import numpy as np

                def sigmoid(z):
                    return 1 / (1 + np.exp(-z))

                def relu(z):
                    return np.maximum(0, z)

                def leaky_relu(z, slope=0.01):
                    return np.where(z > 0, z, slope * z)

                def gelu(z):
                    return 0.5 * z * (1 + np.tanh(np.sqrt(2 / np.pi) * (z + 0.044715 * z ** 3)))"""
            ),
        },
        {
            "title": "Compare outputs",
            "explanation": "Same inputs, very different shapes: squashing, clipping or smoothing.",
            "code": dedent(
                """\
                z = np.array([-3.0, -1.0, 0.0, 1.0, 3.0])
                print("z         ", z.tolist())
                print("sigmoid   ", sigmoid(z).round(3).tolist())
                print("tanh      ", np.tanh(z).round(3).tolist())
                print("relu      ", relu(z).tolist())
                print("leaky_relu", leaky_relu(z).round(3).tolist())
                print("gelu      ", gelu(z).round(3).tolist())"""
            ),
        },
        {
            "title": "Compare gradients",
            "explanation": "σ′(z) = σ(z)(1 − σ(z)) peaks at 0.25; ReLU's slope is 0 or 1.",
            "code": dedent(
                """\
                sigmoid_grad = sigmoid(z) * (1 - sigmoid(z))
                relu_grad = (z > 0).astype(float)
                print("sigmoid'  ", sigmoid_grad.round(3).tolist())
                print("relu'     ", relu_grad.tolist())"""
            ),
        },
        {
            "title": "Watch gradients vanish",
            "explanation": "Backprop multiplies one slope per layer. Even sigmoid's best case "
            "(0.25) collapses fast.",
            "code": dedent(
                """\
                # The vanishing gradient: backprop multiplies one derivative per layer.
                for layers in (2, 5, 10):
                    print(f"{layers:>2} layers  sigmoid at best: {0.25 ** layers:.2e}   relu (active): {1.0 ** layers:.0f}")"""
            ),
        },
        {
            "title": "Softmax for the output layer",
            "explanation": "Turns raw scores into probabilities that add up to 1.",
            "code": dedent(
                """\
                logits = np.array([2.0, 1.0, 0.1])
                softmax = np.exp(logits) / np.exp(logits).sum()
                print("softmax   ", softmax.round(3).tolist(), "sum =", round(softmax.sum(), 3))"""
            ),
        },
    ],
    "expected_output": dedent(
        """\
        z          [-3.0, -1.0, 0.0, 1.0, 3.0]
        sigmoid    [0.047, 0.269, 0.5, 0.731, 0.953]
        tanh       [-0.995, -0.762, 0.0, 0.762, 0.995]
        relu       [0.0, 0.0, 0.0, 1.0, 3.0]
        leaky_relu [-0.03, -0.01, 0.0, 1.0, 3.0]
        gelu       [-0.004, -0.159, 0.0, 0.841, 2.996]
        sigmoid'   [0.045, 0.197, 0.25, 0.197, 0.045]
        relu'      [0.0, 0.0, 0.0, 1.0, 1.0]
         2 layers  sigmoid at best: 6.25e-02   relu (active): 1
         5 layers  sigmoid at best: 9.77e-04   relu (active): 1
        10 layers  sigmoid at best: 9.54e-07   relu (active): 1
        softmax    [0.659, 0.242, 0.099] sum = 1.0"""
    ),
    "mistakes": [
        "Using sigmoid in every hidden layer of a deep network (vanishing gradients).",
        "Putting ReLU on a regression output, so negative predictions become impossible.",
        "Applying softmax and then a loss that expects raw logits (double softmax).",
        "Computing softmax without subtracting the max, which can overflow.",
    ],
    "applications": [
        "ReLU/GELU in almost every modern hidden layer",
        "Sigmoid outputs for binary classifiers and gates in LSTMs",
        "Softmax outputs for multi-class classifiers and attention weights",
    ],
}

INTERVIEW = {
    "questions": [
        {
            "level": "basic",
            "kind": "conceptual",
            "question": "What is an activation function and why do we need one?",
            "answer": "A non-linear function applied to each neuron's weighted sum. Without it, "
            "stacked layers collapse into one linear transformation, so the network couldn't "
            "model non-linear patterns. Activations give networks their expressive power.",
            "interviewer_wants": "Non-linearity, and the collapse-to-linear argument.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
        {
            "level": "basic",
            "kind": "conceptual",
            "question": "Compare sigmoid, tanh and ReLU.",
            "answer": "Sigmoid outputs (0, 1), saturates at both ends, max slope 0.25, not "
            "zero-centred. Tanh outputs (−1, 1), zero-centred, max slope 1, still saturates. "
            "ReLU outputs max(0, z): cheap, no saturation for positives, slope 1 when active, "
            "but zero gradient for negatives (dying ReLU).",
            "interviewer_wants": "Ranges, saturation, slopes, and one weakness of each.",
            "follow_ups": [
                {
                    "question": "Which would you use in hidden layers today?",
                    "answer": "ReLU or a variant (Leaky ReLU, GELU) by default; tanh/sigmoid "
                    "mainly inside gates of recurrent units.",
                }
            ],
            "origin": "ai_generated",
        },
        {
            "level": "intermediate",
            "kind": "math",
            "question": "What is the derivative of the sigmoid, and why does it matter?",
            "answer": "σ′(z) = σ(z)(1 − σ(z)). It peaks at 0.25 when z = 0 and approaches 0 for "
            "large |z|. Because backprop multiplies these derivatives layer by layer, deep "
            "sigmoid networks suffer vanishing gradients.",
            "interviewer_wants": "The formula, its 0.25 maximum, and the link to vanishing "
            "gradients.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
        {
            "level": "intermediate",
            "kind": "scenario",
            "question": "Half the neurons in your ReLU network output 0 for every input. What "
            "happened and how do you fix it?",
            "answer": "Dying ReLUs: their pre-activations became negative for all inputs "
            "(often after a large update from a high learning rate or bad initialisation), so "
            "their gradient is 0 and they stop learning. Fixes: lower the learning rate, use He "
            "initialisation, switch to Leaky ReLU, PReLU, ELU or GELU, or add batch "
            "normalisation.",
            "interviewer_wants": "Diagnosis (zero gradient for negatives) plus several fixes.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
        {
            "level": "intermediate",
            "kind": "practical",
            "question": "Which activation would you use on the output layer for regression, "
            "binary classification and multi-class classification?",
            "answer": "Regression: none (linear output). Binary: sigmoid with binary "
            "cross-entropy. Multi-class (one label): softmax with categorical cross-entropy. "
            "Multi-label: a sigmoid per class.",
            "interviewer_wants": "Correct pairing of output activation and loss for each task.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
        {
            "level": "advanced",
            "kind": "conceptual",
            "question": "Why do transformers often use GELU instead of ReLU?",
            "answer": "GELU, x·Φ(x), is smooth and lets small negative values through with "
            "small weight instead of cutting them to zero. That gives smoother gradients and "
            "has worked better empirically in models like BERT and GPT. Its cost is slightly "
            "more computation.",
            "interviewer_wants": "Smoothness, non-zero handling of negatives, and that the "
            "choice is largely empirical.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
        {
            "level": "advanced",
            "kind": "coding",
            "question": "How do you compute softmax in a numerically stable way?",
            "answer": "Subtract the maximum score before exponentiating: softmax(z) = exp(z − "
            "max(z)) / Σ exp(z − max(z)). It gives the same result mathematically but avoids "
            "overflow for large scores. Frameworks combine softmax with the log in the loss "
            "(log-softmax) for the same reason.",
            "interviewer_wants": "The max-subtraction trick and why it's equivalent.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
    ],
    "takeaways": [
        "Activations add the non-linearity that makes depth useful.",
        "Sigmoid/tanh saturate; sigmoid's slope is at most 0.25 → vanishing gradients.",
        "ReLU is the hidden-layer default; watch for dying ReLUs.",
        "Pick the output activation for the task: linear, sigmoid or softmax.",
    ],
}

QUIZ = {
    "questions": [
        {
            "difficulty": "easy",
            "kind": "concept",
            "prompt": "What is the output range of the sigmoid function?",
            "options": ["−1 to 1", "0 to 1", "0 to infinity", "Any real number"],
            "answer": 1,
            "explanation": "Sigmoid squashes any input into (0, 1).",
        },
        {
            "difficulty": "easy",
            "kind": "math",
            "prompt": "ReLU(−4) = ?",
            "options": ["−4", "0", "4", "0.01"],
            "answer": 1,
            "explanation": "ReLU(z) = max(0, z), so negatives become 0.",
        },
        {
            "difficulty": "medium",
            "kind": "concept",
            "prompt": "Why do deep sigmoid networks train slowly?",
            "options": [
                "Sigmoid is expensive to compute",
                "Its gradients are small, and they shrink layer after layer",
                "It outputs negative numbers",
                "It can't be differentiated",
            ],
            "answer": 1,
            "explanation": "Max slope 0.25 multiplied across layers → vanishing gradients.",
        },
        {
            "difficulty": "medium",
            "kind": "scenario",
            "prompt": "Output layer for classifying images into 10 classes?",
            "options": ["ReLU", "Sigmoid", "Softmax", "No activation"],
            "answer": 2,
            "explanation": "Softmax gives a probability for each class, summing to 1.",
        },
        {
            "difficulty": "medium",
            "kind": "scenario",
            "prompt": "Output layer for predicting house prices?",
            "options": ["Softmax", "Sigmoid", "No activation (linear)", "Tanh"],
            "answer": 2,
            "explanation": "Prices are unbounded numbers; a linear output doesn't restrict them.",
        },
        {
            "difficulty": "hard",
            "kind": "math",
            "prompt": "What is the maximum value of the sigmoid's derivative?",
            "options": ["1", "0.5", "0.25", "0.1"],
            "answer": 2,
            "explanation": "σ′(0) = 0.5 × 0.5 = 0.25.",
        },
        {
            "difficulty": "hard",
            "kind": "concept",
            "prompt": "What problem does Leaky ReLU address?",
            "options": [
                "Exploding gradients",
                "Dying ReLU neurons",
                "Slow computation",
                "Overfitting",
            ],
            "answer": 1,
            "explanation": "A small negative slope keeps a gradient flowing for negative inputs.",
        },
    ]
}

REVISION = {
    "definitions": [
        {
            "term": "Activation function",
            "meaning": "Non-linear function applied after each weighted sum.",
        },
        {
            "term": "Saturation",
            "meaning": "Flat regions with near-zero slope (sigmoid, tanh at the extremes).",
        },
        {"term": "Vanishing gradient", "meaning": "Gradients shrinking through many layers."},
        {"term": "Dying ReLU", "meaning": "A ReLU stuck at 0 with zero gradient."},
        {"term": "Softmax", "meaning": "Scores → probabilities that sum to 1."},
    ],
    "formulas": [
        {"name": "Sigmoid", "expression": "σ(z) = 1 / (1 + e⁻ᶻ)", "meaning": "Range (0, 1)."},
        {
            "name": "Sigmoid slope",
            "expression": "σ′(z) = σ(z)(1 − σ(z))",
            "meaning": "At most 0.25.",
        },
        {"name": "ReLU", "expression": "max(0, z)", "meaning": "Slope 0 or 1."},
        {
            "name": "Softmax",
            "expression": "eᶻⁱ / Σ eᶻʲ",
            "meaning": "Subtract max(z) first for stability.",
        },
    ],
    "comparison": {
        "title": "Activation cheat sheet",
        "columns": ["Function", "Range", "Best for", "Watch out"],
        "rows": [
            ["Sigmoid", "(0, 1)", "Binary output", "Vanishing gradients"],
            ["Tanh", "(−1, 1)", "RNN gates, small nets", "Saturates"],
            ["ReLU", "[0, ∞)", "Hidden layers", "Dying ReLU"],
            ["Leaky ReLU", "(−∞, ∞)", "Hidden layers", "Extra hyperparameter"],
            ["Softmax", "(0, 1), sums to 1", "Multi-class output", "Overflow without max trick"],
        ],
    },
    "mistakes": [
        "Sigmoid in every hidden layer of a deep net.",
        "ReLU on a regression output.",
        "Softmax applied twice (model + loss).",
    ],
    "confusions": [
        {
            "pair": "Sigmoid vs softmax",
            "difference": "Sigmoid: one independent probability per unit; softmax: probabilities across classes that sum to 1.",
        },
    ],
    "takeaways": [
        "Non-linearity is non-negotiable.",
        "ReLU/GELU inside, task-specific activation at the output.",
        "Small slopes multiplied across layers = vanishing gradients.",
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
