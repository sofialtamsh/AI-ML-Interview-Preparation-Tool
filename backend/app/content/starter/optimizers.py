from textwrap import dedent

TOPIC = "deep-learning/optimizers"

LESSON = {
    "tagline": "Rolling downhill to the best weights ⛰️",
    "minutes": 9,
    "level": "beginner",
    "cards": [
        {
            "kind": "hook",
            "emoji": "🌫️",
            "title": "Lost on a foggy mountain",
            "body": "You can't see the valley, but you can feel the slope under your feet. Step "
            "downhill, repeat. That's **gradient descent**, and it's how almost every model "
            "learns.",
            "figure": "loss_bowl",
        },
        {
            "kind": "tldr",
            "emoji": "⚡",
            "title": "In one line",
            "body": "Compute the slope of the loss (the gradient), take a small step the "
            "opposite way, repeat until the loss stops dropping.",
        },
        {
            "kind": "math",
            "emoji": "🧮",
            "title": "The update rule",
            "body": "Every weight moves against its gradient, scaled by the learning rate.",
            "formula": "w ← w − η · ∇L(w)",
            "symbols": [
                {"symbol": "w", "meaning": "the model's weights"},
                {"symbol": "η", "meaning": "learning rate (step size)"},
                {"symbol": "∇L(w)", "meaning": "gradient: direction of steepest increase"},
            ],
        },
        {
            "kind": "intuition",
            "emoji": "👟",
            "title": "Step size is everything",
            "body": "Tiny steps take forever. Huge steps leap over the valley and bounce up the "
            "other side, or even explode. The **learning rate** is the most important knob you'll "
            "tune.",
            "figure": "learning_rate",
        },
        {
            "kind": "example",
            "emoji": "🎒",
            "title": "Batch, stochastic, mini-batch",
            "body": "How much data per step?",
            "bullets": [
                "**Batch GD**: all data per step, smooth but slow",
                "**SGD**: one example per step, fast but noisy",
                "**Mini-batch**: 32-512 examples, the practical sweet spot",
            ],
        },
        {
            "kind": "steps",
            "emoji": "🚀",
            "title": "Smarter optimizers",
            "body": "Upgrades that fix plain gradient descent's weak spots.",
            "bullets": [
                "**Momentum**: remembers past steps, rolls through flat parts and zig-zags",
                "**RMSProp**: shrinks steps for weights with consistently big gradients",
                "**Adam**: momentum + per-weight adaptive steps, the go-to default",
            ],
        },
        {
            "kind": "example",
            "emoji": "📉",
            "title": "Stretched valleys",
            "body": "When the loss is steep one way and flat the other, plain GD zig-zags. "
            "Momentum and Adam take a straighter path, reaching the bottom in far fewer steps.",
            "figure": "loss_bowl",
        },
        {
            "kind": "myth",
            "emoji": "🚩",
            "title": "Myth vs fact",
            "body": "A common overclaim.",
            "myth": "Adam always beats plain SGD.",
            "fact": "Adam usually converges faster with little tuning, but well-tuned SGD with "
            "momentum often generalises as well or better, for example in many vision models.",
        },
        {
            "kind": "interview",
            "emoji": "🎤",
            "title": "What interviewers listen for",
            "body": "Intuition plus the math.",
            "bullets": [
                "The update rule and what each symbol means",
                "Effects of too small vs too large learning rates",
                "Batch vs stochastic vs mini-batch",
                "What momentum and Adam add",
            ],
        },
        {
            "kind": "recap",
            "emoji": "✅",
            "title": "Recap",
            "body": "Go roll a ball down the loss landscape in the playground.",
            "bullets": [
                "w ← w − η∇L(w)",
                "Learning rate: too small = slow, too big = diverge",
                "Mini-batches in practice",
                "Momentum and Adam speed things up",
            ],
        },
    ],
    "key_terms": [
        {"term": "Gradient", "meaning": "Vector of partial derivatives; points uphill."},
        {"term": "Learning rate (η)", "meaning": "How big each update step is."},
        {"term": "Mini-batch", "meaning": "A small subset of data used for one update."},
        {"term": "Momentum", "meaning": "Running average of past gradients that smooths steps."},
        {"term": "Adam", "meaning": "Momentum plus adaptive per-weight step sizes."},
        {"term": "Convergence", "meaning": "When updates stop meaningfully reducing the loss."},
    ],
}

PLAYGROUND = {
    "widget": "gradient_descent",
    "title": "Roll down the loss landscape ⛰️",
    "intro": "The contour map is a loss surface; the centre is the minimum. Click to choose a "
    "start, pick an optimizer and learning rate, then step or play and watch the path.",
    "tasks": [
        {
            "prompt": "Use plain GD with a small learning rate and press Play.",
            "hint": "Learning rate around 0.01.",
            "insight": "It heads the right way but crawls. Too-small steps waste time.",
        },
        {
            "prompt": "Raise the learning rate until the path starts zig-zagging.",
            "hint": "Watch the steep direction of the stretched bowl.",
            "insight": "Big steps overshoot across the steep direction. Push further and the "
            "loss explodes: divergence.",
        },
        {
            "prompt": "Switch to Momentum with the same start.",
            "hint": "Use the Optimizer buttons: Momentum. Keep the same learning rate.",
            "insight": "Momentum builds speed along the long, shallow valley where plain GD "
            "crawls. It swings wider across the steep walls, yet arrives in about half the steps.",
        },
        {
            "prompt": "Try Adam, then compare the step counts.",
            "hint": "The steps-to-minimum counter updates for each run.",
            "insight": "Adam scales each direction's step separately, taking a straighter path "
            "through stretched valleys.",
        },
    ],
}

VIDEO = {
    "title": "Gradient descent & optimizers in 3 minutes",
    "scenes": [
        {
            "title": "The foggy mountain",
            "on_screen": "Feel the slope, step downhill",
            "narration": "Training a model means finding weights with the lowest loss. Picture "
            "standing on a foggy mountain: you can't see the valley, but you can feel the slope. "
            "Step downhill, and repeat. That's gradient descent.",
            "figure": "loss_bowl",
            "seconds": 25,
        },
        {
            "title": "The update rule",
            "on_screen": "w ← w − η·∇L(w)",
            "narration": "The gradient points uphill, so we step the opposite way. Each weight "
            "moves by the learning rate times its gradient. Do it again and again, and the loss "
            "keeps dropping until it settles at a minimum.",
            "seconds": 30,
        },
        {
            "title": "The learning rate",
            "on_screen": "Too small: slow. Too big: boom.",
            "narration": "The learning rate is the step size. Too small and training takes "
            "forever. Too big and you leap past the valley, bouncing higher each time until the "
            "loss explodes. Tuning it is the first thing to try when training misbehaves.",
            "figure": "learning_rate",
            "seconds": 35,
        },
        {
            "title": "How much data per step",
            "on_screen": "Batch · Stochastic · Mini-batch",
            "narration": "Using all the data per step is smooth but slow. One example per step, "
            "stochastic gradient descent, is fast but noisy. In practice we use mini-batches of "
            "a few dozen to a few hundred examples.",
            "seconds": 25,
        },
        {
            "title": "Momentum and Adam",
            "on_screen": "Remember the past, adapt each step",
            "narration": "Momentum keeps a running average of past gradients, so it rolls "
            "through flat stretches and damps zig-zags. Adam adds a separate step size for each "
            "weight. On a stretched valley, both reach the bottom far sooner than plain gradient "
            "descent.",
            "figure": "loss_bowl",
            "seconds": 35,
        },
        {
            "title": "Interview takeaway",
            "on_screen": "Rule · rate · batch · optimizer",
            "narration": "Know the update rule, what a bad learning rate looks like, why we use "
            "mini-batches, and what momentum and Adam add. And remember: Adam is a strong "
            "default, not a guaranteed winner.",
            "seconds": 25,
        },
    ],
}

PYTHON = {
    "packages": ["numpy"],
    "dataset": "No dataset: we optimise two simple loss functions, a one-weight parabola with "
    "its minimum at w = 3, and a stretched two-weight bowl.",
    "steps": [
        {
            "title": "Gradient descent on a parabola",
            "explanation": "loss(w) = (w − 3)² has gradient 2(w − 3). We try four learning "
            "rates for 20 steps each.",
            "code": dedent(
                """\
                import numpy as np

                # Loss with its lowest point at w = 3.
                def loss(w):
                    return (w - 3) ** 2

                def grad(w):
                    return 2 * (w - 3)

                for lr in (0.01, 0.1, 0.9, 1.1):
                    w = 0.0
                    for _ in range(20):
                        w -= lr * grad(w)
                    print(f"lr={lr:<4} after 20 steps: w = {w:10.3f}   loss = {loss(w):.3g}")"""
            ),
        },
        {
            "title": "A stretched bowl",
            "explanation": "Steep in one direction (50), shallow in the other (0.5). We count "
            "steps until the loss drops below 10⁻⁶.",
            "code": dedent(
                """\
                # A stretched bowl: steep in one direction, shallow in the other.
                A = np.array([50.0, 0.5])

                def bowl_grad(p):
                    return 2 * A * p

                def steps_to_converge(update, lr, max_steps=2000):
                    p, state = np.array([1.0, 1.0]), {}
                    for step in range(1, max_steps + 1):
                        p = update(p, bowl_grad(p), lr, state)
                        if np.sum(A * p ** 2) < 1e-6:
                            return step
                    return max_steps"""
            ),
        },
        {
            "title": "Three optimizers",
            "explanation": "Plain GD, momentum (a running sum of gradients) and Adam (momentum "
            "plus per-weight scaling, with bias correction).",
            "code": dedent(
                """\
                def gd(p, g, lr, state):
                    return p - lr * g

                def momentum(p, g, lr, state, beta=0.9):
                    state["v"] = beta * state.get("v", 0) + g
                    return p - lr * state["v"]

                def adam(p, g, lr, state, b1=0.9, b2=0.999, eps=1e-8):
                    state["t"] = state.get("t", 0) + 1
                    state["m"] = b1 * state.get("m", 0) + (1 - b1) * g
                    state["v"] = b2 * state.get("v", 0) + (1 - b2) * g ** 2
                    m_hat = state["m"] / (1 - b1 ** state["t"])
                    v_hat = state["v"] / (1 - b2 ** state["t"])
                    return p - lr * m_hat / (np.sqrt(v_hat) + eps)"""
            ),
        },
        {
            "title": "Race them",
            "explanation": "Each optimizer uses a learning rate tuned for this bowl. Fewer steps "
            "is better.",
            "code": dedent(
                """\
                # Each optimizer uses a learning rate tuned for this bowl.
                for name, update, lr in (("GD", gd, 0.019), ("Momentum", momentum, 0.0185), ("Adam", adam, 0.27)):
                    print(f"{name:<9} lr={lr:<5} steps to reach the minimum: {steps_to_converge(update, lr)}")"""
            ),
        },
    ],
    "expected_output": dedent(
        """\
        lr=0.01 after 20 steps: w =      0.997   loss = 4.01
        lr=0.1  after 20 steps: w =      2.965   loss = 0.0012
        lr=0.9  after 20 steps: w =      2.965   loss = 0.0012
        lr=1.1  after 20 steps: w =   -112.013   loss = 1.32e+04
        GD        lr=0.019 steps to reach the minimum: 343
        Momentum  lr=0.0185 steps to reach the minimum: 88
        Adam      lr=0.27  steps to reach the minimum: 36"""
    ),
    "mistakes": [
        "Keeping the default learning rate without ever tuning it.",
        "Forgetting to zero gradients between steps in frameworks like PyTorch.",
        "Comparing optimizers without tuning each one's learning rate.",
        "Reading lr = 0.9 converging here as 'big rates are fine': it zig-zags, and 1.1 explodes.",
    ],
    "applications": [
        "Training every neural network (SGD, Adam, AdamW)",
        "Fitting linear and logistic regression on large data",
        "Learning-rate schedules and warm-up in LLM training",
    ],
}

INTERVIEW = {
    "questions": [
        {
            "level": "basic",
            "kind": "conceptual",
            "question": "Explain gradient descent.",
            "answer": "An iterative method to minimise a loss: compute the gradient of the loss "
            "with respect to the parameters, then update w ← w − η∇L(w), where η is the learning "
            "rate. Repeat until the loss stops decreasing. The gradient points uphill, so moving "
            "against it reduces the loss.",
            "interviewer_wants": "The update rule, the role of the learning rate, and why the "
            "minus sign.",
            "follow_ups": [
                {
                    "question": "Does it always find the global minimum?",
                    "answer": "Only for convex losses (like linear regression's MSE). Neural "
                    "network losses are non-convex, so it finds a good local minimum or saddle "
                    "region, which is usually good enough.",
                }
            ],
            "origin": "ai_generated",
        },
        {
            "level": "basic",
            "kind": "scenario",
            "question": "What happens if the learning rate is too small or too large?",
            "answer": "Too small: training is very slow and may stall on plateaus. Too large: "
            "updates overshoot the minimum, the loss oscillates or diverges to infinity/NaN. A "
            "learning-rate range test or a schedule (warm-up, decay) helps find a good value.",
            "interviewer_wants": "Both failure modes and a practical way to choose the rate.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
        {
            "level": "intermediate",
            "kind": "conceptual",
            "question": "Compare batch, stochastic and mini-batch gradient descent.",
            "answer": "Batch uses the whole dataset per update: accurate gradient, smooth "
            "progress, but slow and memory-heavy. SGD uses one example: cheap, noisy updates "
            "that can escape shallow minima but converge erratically. Mini-batch (e.g. 32-512 "
            "examples) balances the two and uses GPUs efficiently; it's the default.",
            "interviewer_wants": "Trade-offs in noise, speed and memory, and why mini-batch "
            "wins in practice.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
        {
            "level": "intermediate",
            "kind": "math",
            "question": "How does momentum change the update?",
            "answer": "It keeps a velocity v ← βv + ∇L(w) and updates w ← w − ηv, with β "
            "around 0.9. Consistent gradient directions accumulate speed while oscillating "
            "components cancel, so it moves faster along shallow valleys and damps zig-zags.",
            "interviewer_wants": "The velocity equations and the intuition of accumulating "
            "consistent directions.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
        {
            "level": "intermediate",
            "kind": "conceptual",
            "question": "What does Adam do differently?",
            "answer": "Adam tracks a moving average of gradients (first moment, like momentum) "
            "and of squared gradients (second moment). Each weight's step is scaled by the first "
            "moment divided by the square root of the second, so weights with large or noisy "
            "gradients take smaller steps. Bias correction fixes the averages being biased "
            "towards zero early on.",
            "interviewer_wants": "Both moments, per-parameter adaptive steps, and bias correction.",
            "follow_ups": [
                {
                    "question": "What is AdamW?",
                    "answer": "Adam with decoupled weight decay: the decay is applied directly "
                    "to the weights instead of through the gradient, which regularises more "
                    "correctly with adaptive steps.",
                }
            ],
            "origin": "ai_generated",
        },
        {
            "level": "advanced",
            "kind": "scenario",
            "question": "Your training loss suddenly becomes NaN. What do you check?",
            "answer": "Likely exploding values: lower the learning rate, add gradient clipping, "
            "check for log(0) or division by zero in the loss, use numerically stable functions "
            "(log-softmax), check inputs for NaNs or extreme values, and consider mixed-precision "
            "overflow (use loss scaling).",
            "interviewer_wants": "Learning rate and gradient explosion first, then numerical "
            "stability causes.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
        {
            "level": "advanced",
            "kind": "practical",
            "question": "Why do we use learning-rate schedules like warm-up and cosine decay?",
            "answer": "Warm-up starts with a small rate to avoid unstable early updates (Adam's "
            "statistics are noisy at first). Decay lowers the rate later so training settles "
            "into a minimum instead of bouncing around it. Cosine decay and step decay are "
            "common; LLM training typically uses warm-up then cosine decay.",
            "interviewer_wants": "Why early and late training need different step sizes.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
    ],
    "takeaways": [
        "Update: w ← w − η∇L(w); the gradient points uphill.",
        "Learning rate too small = slow, too large = oscillation or divergence.",
        "Mini-batch SGD is the practical default.",
        "Momentum smooths and speeds up; Adam adds per-weight adaptive steps.",
    ],
}

QUIZ = {
    "questions": [
        {
            "difficulty": "easy",
            "kind": "concept",
            "prompt": "Why does gradient descent step against the gradient?",
            "options": [
                "The gradient points toward the minimum",
                "The gradient points uphill, so the opposite way goes downhill",
                "To make the weights smaller",
                "It's arbitrary",
            ],
            "answer": 1,
            "explanation": "The gradient is the direction of steepest increase of the loss.",
        },
        {
            "difficulty": "easy",
            "kind": "scenario",
            "prompt": "The loss jumps around and grows each step. Most likely cause?",
            "options": [
                "Learning rate too small",
                "Learning rate too large",
                "Too much data",
                "The model is too simple",
            ],
            "answer": 1,
            "explanation": "Oversized steps overshoot the minimum and can diverge.",
        },
        {
            "difficulty": "medium",
            "kind": "math",
            "prompt": "w = 5, gradient = 4, learning rate = 0.5. After one step, w = ?",
            "options": ["3", "7", "4.5", "1"],
            "answer": 0,
            "explanation": "5 − 0.5 × 4 = 3.",
        },
        {
            "difficulty": "medium",
            "kind": "concept",
            "prompt": "Mini-batch gradient descent uses…",
            "options": [
                "All examples per update",
                "One example per update",
                "A small subset of examples per update",
                "No gradients",
            ],
            "answer": 2,
            "explanation": "A mini-batch (e.g. 64 examples) balances accuracy and speed.",
        },
        {
            "difficulty": "medium",
            "kind": "concept",
            "prompt": "What does momentum accumulate?",
            "options": [
                "Past losses",
                "A running average of past gradients",
                "The learning rate",
                "The number of epochs",
            ],
            "answer": 1,
            "explanation": "The velocity term builds up consistent gradient directions.",
        },
        {
            "difficulty": "hard",
            "kind": "concept",
            "prompt": "What extra information does Adam track compared with momentum?",
            "options": [
                "The squared gradients (second moment)",
                "The validation loss",
                "The number of layers",
                "Nothing extra",
            ],
            "answer": 0,
            "explanation": "The second moment scales each weight's step size individually.",
        },
        {
            "difficulty": "hard",
            "kind": "code",
            "prompt": "With loss (w − 3)², which learning rate makes this loop diverge?",
            "code": "for _ in range(20):\n    w -= lr * 2 * (w - 3)",
            "options": ["0.01", "0.1", "0.9", "1.1"],
            "answer": 3,
            "explanation": "Each step multiplies the error by (1 − 2·lr); |1 − 2.2| > 1 so it "
            "grows.",
        },
    ]
}

REVISION = {
    "definitions": [
        {"term": "Gradient", "meaning": "Partial derivatives of the loss; points uphill."},
        {"term": "Learning rate", "meaning": "Step size of each update."},
        {"term": "SGD", "meaning": "Gradient descent on one example or a mini-batch per step."},
        {"term": "Momentum", "meaning": "Velocity built from past gradients."},
        {"term": "Adam", "meaning": "Momentum + per-weight adaptive steps + bias correction."},
    ],
    "formulas": [
        {
            "name": "Gradient descent",
            "expression": "w ← w − η·∇L(w)",
            "meaning": "Step against the gradient.",
        },
        {"name": "Momentum", "expression": "v ← βv + ∇L;  w ← w − ηv", "meaning": "β ≈ 0.9."},
        {
            "name": "Adam step",
            "expression": "w ← w − η·m̂ / (√v̂ + ε)",
            "meaning": "m̂, v̂: bias-corrected moments.",
        },
    ],
    "comparison": {
        "title": "Optimizers at a glance",
        "columns": ["Optimizer", "Idea", "Strength", "Watch out"],
        "rows": [
            [
                "GD / SGD",
                "Step against the gradient",
                "Simple, generalises well",
                "Needs rate tuning",
            ],
            ["Momentum", "Add velocity", "Faster in valleys", "Can overshoot"],
            [
                "Adam",
                "Momentum + adaptive steps",
                "Fast, little tuning",
                "Not always best final accuracy",
            ],
        ],
    },
    "mistakes": [
        "Never tuning the learning rate.",
        "Comparing optimizers at one shared learning rate.",
        "Ignoring NaN losses instead of lowering the rate or clipping.",
    ],
    "confusions": [
        {
            "pair": "Epoch vs step",
            "difference": "An epoch passes over all data; a step is one parameter update (one batch).",
        },
        {
            "pair": "Learning rate vs momentum β",
            "difference": "η scales each step; β sets how much past gradients carry over.",
        },
    ],
    "takeaways": [
        "The learning rate matters most.",
        "Mini-batches in practice.",
        "Adam is the default; tuned SGD+momentum is a strong rival.",
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
