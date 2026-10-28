from textwrap import dedent

TOPIC = "deep-learning/neural-network-fundamentals"

LESSON = {
    "tagline": "Tiny calculators that team up to learn anything 🧠",
    "minutes": 10,
    "level": "beginner",
    "cards": [
        {
            "kind": "hook",
            "emoji": "📸",
            "title": "Face unlock, voice notes, ChatGPT…",
            "body": "All run on neural networks. Underneath the hype, each one is just layers "
            "of tiny calculators called **neurons**, passing numbers forward.",
            "figure": "network",
        },
        {
            "kind": "tldr",
            "emoji": "⚡",
            "title": "In one line",
            "body": "Each neuron does a weighted sum + bias, squashes it with an activation, and "
            "passes it on. Training tunes all the weights so the final output is right.",
        },
        {
            "kind": "math",
            "emoji": "🔢",
            "title": "One neuron",
            "body": "Multiply each input by its weight, add them up with a bias, then apply an "
            "activation function.",
            "formula": "a = σ(w·x + b)",
            "symbols": [
                {"symbol": "x", "meaning": "inputs coming in"},
                {"symbol": "w", "meaning": "weights: how much each input matters"},
                {"symbol": "b", "meaning": "bias: shifts the threshold"},
                {"symbol": "σ", "meaning": "activation (adds non-linearity)"},
                {"symbol": "a", "meaning": "the neuron's output"},
            ],
            "figure": "neuron",
        },
        {
            "kind": "intuition",
            "emoji": "🎚️",
            "title": "Weights are volume knobs",
            "body": "A big positive weight says 'this input matters, turn it up'. A negative "
            "weight says 'this input argues against'. Learning = finding the right knob settings.",
        },
        {
            "kind": "steps",
            "emoji": "➡️",
            "title": "Forward pass",
            "body": "Data flows one way to make a prediction.",
            "bullets": [
                "**Input layer**: the raw features",
                "**Hidden layers**: neurons combine features into patterns",
                "**Output layer**: the prediction (a probability, a class, a number)",
            ],
            "figure": "network",
        },
        {
            "kind": "steps",
            "emoji": "🔁",
            "title": "How it learns",
            "body": "The training loop, on repeat.",
            "bullets": [
                "Forward pass → prediction",
                "**Loss**: how wrong was it?",
                "**Backpropagation**: chain rule finds each weight's share of the blame",
                "**Gradient descent**: nudge every weight to reduce the loss",
            ],
            "figure": "loss_bowl",
        },
        {
            "kind": "example",
            "emoji": "❌",
            "title": "Why one neuron isn't enough",
            "body": "XOR (true when exactly one input is on) can't be split by one straight line. "
            "Add a hidden layer and the network bends the boundary, solving it easily.",
        },
        {
            "kind": "myth",
            "emoji": "🚩",
            "title": "Myth vs fact",
            "body": "The non-linearity is the whole point.",
            "myth": "Stacking more layers always makes a network more powerful.",
            "fact": "Without non-linear activations, any stack of layers collapses into one "
            "linear function. Depth only helps because of the activations in between.",
        },
        {
            "kind": "interview",
            "emoji": "🎤",
            "title": "What interviewers listen for",
            "body": "Mechanics first, buzzwords last.",
            "bullets": [
                "Weighted sum + bias + activation",
                "Forward pass vs backpropagation",
                "Why non-linearity is essential",
                "Counting parameters in a layer",
            ],
        },
        {
            "kind": "recap",
            "emoji": "✅",
            "title": "Recap",
            "body": "Go train a tiny network in the playground.",
            "bullets": [
                "Neuron = σ(w·x + b)",
                "Layers pass outputs forward",
                "Backprop + gradient descent update the weights",
                "Activations make depth useful",
            ],
        },
    ],
    "key_terms": [
        {"term": "Neuron", "meaning": "Weighted sum of inputs plus bias, through an activation."},
        {"term": "Weight", "meaning": "A learnable number scaling one input."},
        {"term": "Bias", "meaning": "A learnable offset added before the activation."},
        {"term": "Forward pass", "meaning": "Computing outputs layer by layer from the inputs."},
        {
            "term": "Backpropagation",
            "meaning": "Using the chain rule to get every weight's gradient.",
        },
        {"term": "Epoch", "meaning": "One pass over the whole training set."},
    ],
}

PLAYGROUND = {
    "widget": "neural_network",
    "title": "Train a tiny brain 🧠",
    "intro": "A 2-input network with one hidden layer, learning a pattern you pick. Watch the "
    "weights (lines) change colour and thickness, the loss fall, and the decision map take "
    "shape.",
    "tasks": [
        {
            "prompt": "Pick the XOR pattern and set hidden neurons to 1. Press Train.",
            "hint": "Use the hidden-neurons slider, then Train.",
            "insight": "With one hidden neuron the boundary is basically a single line, and XOR "
            "needs two. The loss gets stuck.",
        },
        {
            "prompt": "Now give it 4 hidden neurons and train again.",
            "hint": "Reset, set 4 neurons, Train.",
            "insight": "More hidden neurons let the network combine several lines into a "
            "curved boundary. XOR gets solved.",
        },
        {
            "prompt": "Switch the activation to Linear and train on XOR.",
            "hint": "Use the Activation buttons: Linear.",
            "insight": "No matter how many neurons, a linear network can only draw a straight "
            "line. Non-linearity is what makes depth matter.",
        },
        {
            "prompt": "Set the learning rate very high and train.",
            "hint": "Drag the learning-rate slider to the right.",
            "insight": "The loss jumps around instead of falling smoothly: steps that are too "
            "big overshoot the minimum.",
        },
    ],
}

VIDEO = {
    "title": "Neural networks in 3 minutes",
    "scenes": [
        {
            "title": "It's all neurons",
            "on_screen": "Layers of tiny calculators",
            "narration": "Face unlock, translation, chatbots. All neural networks. Strip away "
            "the hype and you find layers of simple units called neurons, each passing a "
            "number to the next layer.",
            "figure": "network",
            "seconds": 25,
        },
        {
            "title": "Inside one neuron",
            "on_screen": "a = σ(w·x + b)",
            "narration": "A neuron multiplies each input by a weight, adds them up with a bias, "
            "and passes the result through an activation function. Weights say how much each "
            "input matters. The bias shifts the threshold.",
            "figure": "neuron",
            "seconds": 30,
        },
        {
            "title": "The forward pass",
            "on_screen": "Input → hidden → output",
            "narration": "Data enters the input layer, flows through hidden layers that build "
            "up patterns, and reaches the output layer, which makes the prediction. That one-way "
            "trip is the forward pass.",
            "figure": "network",
            "seconds": 30,
        },
        {
            "title": "Learning from mistakes",
            "on_screen": "Loss → backprop → update",
            "narration": "We measure how wrong the prediction is with a loss. Backpropagation "
            "uses the chain rule to work out how much each weight contributed, and gradient "
            "descent nudges every weight to make the loss smaller. Repeat thousands of times.",
            "figure": "loss_bowl",
            "seconds": 35,
        },
        {
            "title": "Why activations matter",
            "on_screen": "No non-linearity = just a line",
            "narration": "Without activation functions, stacking layers achieves nothing: the "
            "whole network collapses into one linear function. Activations let networks bend "
            "their decision boundaries, which is how they solve problems like XOR.",
            "figure": "activation_curves",
            "seconds": 30,
        },
        {
            "title": "Interview takeaway",
            "on_screen": "Sum, squash, pass forward, learn backward",
            "narration": "In interviews, explain the neuron equation, the forward pass, how "
            "backpropagation and gradient descent train the weights, and why non-linear "
            "activations are essential. Bonus points for counting the parameters in a layer.",
            "seconds": 25,
        },
    ],
}

PYTHON = {
    "packages": ["numpy"],
    "dataset": "The four XOR examples: inputs (0,0), (0,1), (1,0), (1,1) with outputs 0, 1, 1, 0. "
    "Everything is built from scratch with NumPy.",
    "steps": [
        {
            "title": "One neuron by hand",
            "explanation": "Weighted sum plus bias, then the sigmoid activation squashes it "
            "between 0 and 1.",
            "code": dedent(
                """\
                import numpy as np

                def sigmoid(z):
                    return 1 / (1 + np.exp(-z))

                # One neuron: weighted sum, then activation.
                x = np.array([1.0, 2.0])
                w = np.array([0.5, -0.25])
                b = 0.1
                z = x @ w + b
                print(f"z = {z:.2f}, output = {sigmoid(z):.3f}")"""
            ),
        },
        {
            "title": "A network for XOR",
            "explanation": "2 inputs → 4 hidden neurons (tanh) → 1 output (sigmoid). Weights "
            "start random; biases start at zero.",
            "code": dedent(
                """\
                # XOR: no single straight line separates it, so we need a hidden layer.
                X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=float)
                y = np.array([[0], [1], [1], [0]], dtype=float)

                rng = np.random.default_rng(1)
                W1, b1 = rng.normal(0, 1, (2, 4)), np.zeros((1, 4))
                W2, b2 = rng.normal(0, 1, (4, 1)), np.zeros((1, 1))

                def forward(X):
                    h = np.tanh(X @ W1 + b1)          # hidden layer
                    out = sigmoid(h @ W2 + b2)        # output layer
                    return h, out"""
            ),
        },
        {
            "title": "Train with backpropagation",
            "explanation": "Forward pass, mean squared error, then the chain rule gives each "
            "weight's gradient. Every step moves the weights a little downhill (learning rate 1.0).",
            "code": dedent(
                """\
                for epoch in range(3001):
                    h, out = forward(X)
                    loss = np.mean((out - y) ** 2)
                    d_out = 2 * (out - y) / len(X) * out * (1 - out)
                    d_h = d_out @ W2.T * (1 - h ** 2)
                    W2 -= 1.0 * h.T @ d_out
                    b2 -= 1.0 * d_out.sum(axis=0, keepdims=True)
                    W1 -= 1.0 * X.T @ d_h
                    b1 -= 1.0 * d_h.sum(axis=0, keepdims=True)
                    if epoch % 1000 == 0:
                        print(f"epoch {epoch:>4}  loss {loss:.3f}")"""
            ),
        },
        {
            "title": "Check the predictions",
            "explanation": "Outputs close to 0, 1, 1, 0 mean the network learned XOR.",
            "code": dedent(
                """\
                _, out = forward(X)
                print("XOR predictions:", out.round(2).ravel().tolist())"""
            ),
        },
    ],
    "expected_output": dedent(
        """\
        z = 0.10, output = 0.525
        epoch    0  loss 0.240
        epoch 1000  loss 0.001
        epoch 2000  loss 0.000
        epoch 3000  loss 0.000
        XOR predictions: [0.01, 0.98, 0.98, 0.02]"""
    ),
    "mistakes": [
        "Initialising all weights to the same value, so every neuron learns the same thing.",
        "Forgetting the activation's derivative in backpropagation.",
        "Mixing up matrix shapes: check (samples, features) at every layer.",
        "Using a learning rate so large the loss bounces or explodes.",
    ],
    "applications": [
        "Image and speech recognition",
        "Recommendation and ranking models",
        "The building block behind transformers and LLMs",
    ],
}

INTERVIEW = {
    "questions": [
        {
            "level": "basic",
            "kind": "conceptual",
            "question": "What does a single neuron compute?",
            "answer": "A weighted sum of its inputs plus a bias, passed through an activation "
            "function: a = σ(w·x + b). The weights and bias are learned; the activation adds "
            "non-linearity.",
            "interviewer_wants": "The formula and the role of weights, bias and activation.",
            "follow_ups": [
                {
                    "question": "What does the bias do?",
                    "answer": "It shifts the activation's input, letting the neuron fire even "
                    "when all inputs are zero, like the intercept in a line.",
                }
            ],
            "origin": "ai_generated",
        },
        {
            "level": "basic",
            "kind": "conceptual",
            "question": "What's the difference between the forward pass and backpropagation?",
            "answer": "The forward pass computes predictions by passing inputs through the "
            "layers. Backpropagation goes the other way: it applies the chain rule from the loss "
            "back through the layers to compute the gradient of the loss with respect to every "
            "weight. An optimiser then uses those gradients to update the weights.",
            "interviewer_wants": "Direction of each pass and that backprop computes gradients, "
            "while the optimiser updates.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
        {
            "level": "intermediate",
            "kind": "conceptual",
            "question": "Why do neural networks need non-linear activation functions?",
            "answer": "A composition of linear layers is itself linear: W2(W1x + b1) + b2 = "
            "Wx + b. So without non-linear activations a deep network is no more expressive "
            "than a single linear model and can't learn patterns like XOR. Non-linearities let "
            "networks approximate complex functions.",
            "interviewer_wants": "The collapse-to-linear argument and an example like XOR.",
            "follow_ups": [
                {
                    "question": "What does the universal approximation theorem say?",
                    "answer": "A network with one hidden layer and enough neurons can "
                    "approximate any continuous function on a bounded region to any accuracy; it "
                    "says nothing about how easy that is to learn.",
                }
            ],
            "origin": "ai_generated",
        },
        {
            "level": "intermediate",
            "kind": "math",
            "question": "How many parameters does a dense layer from 128 inputs to 64 outputs have?",
            "answer": "128 × 64 weights plus 64 biases = 8,192 + 64 = 8,256 parameters.",
            "interviewer_wants": "inputs × outputs + outputs, done quickly.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
        {
            "level": "intermediate",
            "kind": "scenario",
            "question": "What happens if you initialise all weights to zero?",
            "answer": "Every neuron in a layer computes the same output and receives the same "
            "gradient, so they stay identical forever (the symmetry problem). Use small random "
            "initialisation, for example Xavier/Glorot for tanh or He initialisation for ReLU.",
            "interviewer_wants": "Symmetry breaking and named initialisation schemes.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
        {
            "level": "advanced",
            "kind": "math",
            "question": "Walk through backpropagation for one hidden layer.",
            "answer": "Forward: h = f(XW1 + b1), ŷ = g(hW2 + b2), loss L. Backward: compute "
            "δ_out = ∂L/∂ŷ ⊙ g′, then ∂L/∂W2 = hᵀδ_out and ∂L/∂b2 = Σδ_out. Propagate: δ_h = "
            "δ_out W2ᵀ ⊙ f′, then ∂L/∂W1 = Xᵀδ_h and ∂L/∂b1 = Σδ_h. Each step is the chain rule, "
            "reusing values stored in the forward pass.",
            "interviewer_wants": "Correct chain-rule ordering, the element-wise activation "
            "derivatives, and reuse of forward values.",
            "follow_ups": [
                {
                    "question": "Why is backprop efficient?",
                    "answer": "It reuses intermediate results, so computing all gradients costs "
                    "about as much as one forward pass, instead of one pass per weight.",
                }
            ],
            "origin": "ai_generated",
        },
        {
            "level": "advanced",
            "kind": "practical",
            "question": "Your network's training loss isn't decreasing at all. What do you check?",
            "answer": "Overfit a tiny batch first; if that fails, there's a bug. Check the "
            "learning rate (too high or too low), weight initialisation, that inputs are "
            "normalised, the loss and activation pairing (e.g. sigmoid output with binary "
            "cross-entropy), gradients for NaNs or zeros, dead ReLUs, and that labels line up "
            "with inputs.",
            "interviewer_wants": "A systematic debugging order, starting with overfitting a "
            "small batch.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
    ],
    "takeaways": [
        "Neuron = activation(weighted sum + bias).",
        "Forward pass predicts; backprop computes gradients; the optimiser updates weights.",
        "Non-linear activations are what make depth useful.",
        "Dense layer parameters = inputs × outputs + outputs.",
    ],
}

QUIZ = {
    "questions": [
        {
            "difficulty": "easy",
            "kind": "concept",
            "prompt": "What does a neuron compute before its activation?",
            "options": [
                "The maximum input",
                "A weighted sum of inputs plus a bias",
                "The average of its weights",
                "A random number",
            ],
            "answer": 1,
            "explanation": "z = w·x + b, then the activation is applied to z.",
        },
        {
            "difficulty": "easy",
            "kind": "concept",
            "prompt": "Which step computes how much each weight contributed to the error?",
            "options": ["Forward pass", "Backpropagation", "Data loading", "Prediction"],
            "answer": 1,
            "explanation": "Backpropagation applies the chain rule from the loss back to every "
            "weight.",
        },
        {
            "difficulty": "medium",
            "kind": "concept",
            "prompt": "A 5-layer network uses no activation functions. It is equivalent to…",
            "options": [
                "A 5-times more powerful model",
                "A single linear model",
                "A decision tree",
                "An unsupervised model",
            ],
            "answer": 1,
            "explanation": "Linear layers compose into one linear function.",
        },
        {
            "difficulty": "medium",
            "kind": "math",
            "prompt": "How many parameters in a dense layer from 10 inputs to 3 outputs?",
            "options": ["13", "30", "33", "300"],
            "answer": 2,
            "explanation": "10 × 3 weights + 3 biases = 33.",
        },
        {
            "difficulty": "medium",
            "kind": "scenario",
            "prompt": "Why can't a single neuron (no hidden layer) learn XOR?",
            "options": [
                "XOR has too many examples",
                "XOR isn't linearly separable",
                "Neurons can't output 0",
                "XOR needs a bigger learning rate",
            ],
            "answer": 1,
            "explanation": "No single straight line separates XOR's classes.",
        },
        {
            "difficulty": "hard",
            "kind": "scenario",
            "prompt": "All weights start at exactly 0. What happens in training?",
            "options": [
                "Training is faster",
                "Neurons in a layer stay identical",
                "The network overfits immediately",
                "Nothing; it's the recommended setting",
            ],
            "answer": 1,
            "explanation": "Same inputs and gradients keep them identical: symmetry is never "
            "broken.",
        },
        {
            "difficulty": "hard",
            "kind": "code",
            "prompt": "In this line, what does (1 - h ** 2) represent?",
            "code": "d_h = d_out @ W2.T * (1 - h ** 2)",
            "options": [
                "The loss",
                "The derivative of tanh at the hidden layer",
                "The learning rate",
                "A regularisation term",
            ],
            "answer": 1,
            "explanation": "d/dz tanh(z) = 1 − tanh²(z), and h = tanh(z).",
        },
    ]
}

REVISION = {
    "definitions": [
        {"term": "Neuron", "meaning": "Computes σ(w·x + b)."},
        {
            "term": "Hidden layer",
            "meaning": "Neurons between input and output that build features.",
        },
        {"term": "Loss", "meaning": "A number measuring how wrong predictions are."},
        {
            "term": "Backpropagation",
            "meaning": "Chain rule from the loss to every weight's gradient.",
        },
        {"term": "Epoch", "meaning": "One full pass over the training data."},
    ],
    "formulas": [
        {
            "name": "Neuron",
            "expression": "a = σ(w·x + b)",
            "meaning": "Weighted sum, bias, activation.",
        },
        {
            "name": "Layer",
            "expression": "h = σ(XW + b)",
            "meaning": "All neurons of a layer at once.",
        },
        {
            "name": "Update",
            "expression": "w ← w − η·∂L/∂w",
            "meaning": "Gradient descent step with learning rate η.",
        },
        {
            "name": "Dense params",
            "expression": "inputs × outputs + outputs",
            "meaning": "Weights plus biases.",
        },
    ],
    "comparison": {
        "title": "Forward pass vs backpropagation",
        "columns": ["", "Forward pass", "Backpropagation"],
        "rows": [
            ["Direction", "Input → output", "Loss → input"],
            ["Computes", "Predictions", "Gradients"],
            ["Uses", "Weights and activations", "Chain rule + stored forward values"],
        ],
    },
    "mistakes": [
        "Zero (symmetric) weight initialisation.",
        "Dropping activations and expecting depth to help.",
        "Shape mismatches between layers.",
    ],
    "confusions": [
        {
            "pair": "Backprop vs gradient descent",
            "difference": "Backprop computes gradients; gradient descent uses them to update weights.",
        },
        {
            "pair": "Epoch vs iteration",
            "difference": "Epoch = full dataset pass; iteration = one batch update.",
        },
    ],
    "takeaways": [
        "σ(w·x + b) is the atom of deep learning.",
        "Non-linearity makes layers worth stacking.",
        "Training = forward, loss, backprop, update, repeat.",
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
