from textwrap import dedent

TOPIC = "machine-learning/regression"

LESSON = {
    "tagline": "Draw the best straight line through the chaos 📈",
    "minutes": 9,
    "level": "beginner",
    "cards": [
        {
            "kind": "hook",
            "emoji": "🏠",
            "title": "Guess the rent",
            "body": "Bigger flat, higher rent. Roughly. **Linear regression** turns that 'roughly' "
            "into a line you can use: give it a size, get a predicted rent.",
            "figure": "scatter_line",
        },
        {
            "kind": "tldr",
            "emoji": "⚡",
            "title": "In one line",
            "body": "Fit the straight line that keeps the **squared errors** as small as "
            "possible, then use it to predict numbers.",
        },
        {
            "kind": "math",
            "emoji": "🧮",
            "title": "The whole model",
            "body": "Two numbers to learn: how steep the line is and where it starts.",
            "formula": "ŷ = w·x + b",
            "symbols": [
                {"symbol": "x", "meaning": "input (flat size)"},
                {"symbol": "ŷ", "meaning": "predicted output (rent)"},
                {"symbol": "w", "meaning": "slope: rent added per extra m²"},
                {"symbol": "b", "meaning": "intercept: the line's value at x = 0"},
            ],
        },
        {
            "kind": "intuition",
            "emoji": "📏",
            "title": "Residuals = how wrong you are",
            "body": "For each point, the gap between the real value and the line is a "
            "**residual**. Square them so big misses hurt more and signs don't cancel, then "
            "average: that's MSE.",
            "figure": "residuals",
        },
        {
            "kind": "math",
            "emoji": "🎯",
            "title": "The score to beat",
            "body": "Training finds the w and b with the smallest MSE. For one feature there's "
            "even a closed form: w = cov(x, y) / var(x).",
            "formula": "MSE = (1/n) Σ (yᵢ − ŷᵢ)²",
            "symbols": [
                {"symbol": "yᵢ", "meaning": "true value of example i"},
                {"symbol": "ŷᵢ", "meaning": "the line's prediction"},
                {"symbol": "n", "meaning": "number of examples"},
            ],
        },
        {
            "kind": "steps",
            "emoji": "🛠️",
            "title": "Two ways to fit it",
            "body": "Same answer, different routes.",
            "bullets": [
                "**Normal equation**: solve for w and b directly (great for small data)",
                "**Gradient descent**: nudge w and b downhill on the MSE (scales to huge data)",
            ],
            "figure": "loss_bowl",
        },
        {
            "kind": "example",
            "emoji": "📊",
            "title": "How good is the fit?",
            "body": "**R²** says what share of the variation your line explains: 1 = perfect, "
            "0 = no better than always predicting the average.",
        },
        {
            "kind": "myth",
            "emoji": "🚩",
            "title": "Myth vs fact",
            "body": "Squared errors have a side effect.",
            "myth": "One weird data point can't change the line much.",
            "fact": "Squaring makes far-off points (outliers) pull hard on the line. Check for "
            "them, or use a robust loss like Huber.",
        },
        {
            "kind": "interview",
            "emoji": "🎤",
            "title": "What interviewers listen for",
            "body": "Formulas plus judgment.",
            "bullets": [
                "ŷ = w·x + b and what w, b mean",
                "Why minimise squared error",
                "R² and MSE in plain words",
                "Assumptions and outliers",
            ],
        },
        {
            "kind": "recap",
            "emoji": "✅",
            "title": "Recap",
            "body": "Now drag some points around in the playground.",
            "bullets": [
                "A line: ŷ = w·x + b",
                "Fit by minimising MSE",
                "R² measures explained variation",
                "Outliers pull the line",
            ],
        },
    ],
    "key_terms": [
        {"term": "Slope (w)", "meaning": "Change in prediction for a one-unit change in x."},
        {"term": "Intercept (b)", "meaning": "Prediction when x is 0."},
        {"term": "Residual", "meaning": "True value minus predicted value."},
        {"term": "MSE", "meaning": "Mean of squared residuals."},
        {"term": "R²", "meaning": "Share of the variance in y explained by the model."},
    ],
}

PLAYGROUND = {
    "widget": "linear_regression",
    "title": "Fit the line yourself 📈",
    "intro": "Drag the slope and intercept to fit the points by hand, then let least squares do "
    "it. The red bars are residuals; the squares show what MSE adds up.",
    "tasks": [
        {
            "prompt": "Use the sliders to make the MSE as small as you can.",
            "hint": "Get the slope right first, then shift the line up or down.",
            "insight": "You're doing what training does: searching for the w and b with the "
            "smallest error.",
        },
        {
            "prompt": "Press Best fit and compare its MSE with yours.",
            "hint": "Best fit uses the least-squares formula.",
            "insight": "Least squares finds the exact minimum, so you can never beat it on "
            "this data.",
        },
        {
            "prompt": "Add one point far above the others.",
            "hint": "Click high up on the chart.",
            "insight": "The best-fit line tilts toward it. Squared errors make outliers pull "
            "hard on the fit.",
        },
        {
            "prompt": "Switch on Show squares and watch them as you move the line.",
            "hint": "Each square's area is a residual squared.",
            "insight": "MSE is literally the average area of these squares. Big misses dominate.",
        },
    ],
}

VIDEO = {
    "title": "Linear regression in 3 minutes",
    "scenes": [
        {
            "title": "Predicting a number",
            "on_screen": "Size in → rent out",
            "narration": "Linear regression predicts a number from inputs. Give it a flat's "
            "size, it predicts the rent. It does this by drawing the straight line that best "
            "fits past examples.",
            "figure": "scatter_line",
            "seconds": 25,
        },
        {
            "title": "Two knobs",
            "on_screen": "ŷ = w·x + b",
            "narration": "The line has two knobs. The slope w says how much the prediction "
            "rises for each extra square metre. The intercept b shifts the whole line up or "
            "down. Learning means finding good values for both.",
            "seconds": 30,
        },
        {
            "title": "Measuring mistakes",
            "on_screen": "Residual = real − predicted",
            "narration": "For every point, the gap between the real value and the line is a "
            "residual. We square each residual and average them. That's the mean squared error. "
            "Squaring stops positive and negative errors cancelling out and punishes big misses.",
            "figure": "residuals",
            "seconds": 35,
        },
        {
            "title": "Finding the best line",
            "on_screen": "Minimise MSE",
            "narration": "The best line has the smallest MSE. With one feature you can solve it "
            "directly: slope equals covariance over variance. For huge datasets, gradient "
            "descent walks downhill on the error until it reaches the bottom.",
            "figure": "loss_bowl",
            "seconds": 35,
        },
        {
            "title": "How good is it?",
            "on_screen": "R² = explained variation",
            "narration": "R squared tells you how much of the ups and downs in rent your line "
            "explains. One is perfect, zero means you'd do just as well predicting the average "
            "every time.",
            "seconds": 25,
        },
        {
            "title": "Interview takeaway",
            "on_screen": "Line, loss, fit, and its weak spots",
            "narration": "Know the equation, why we minimise squared error, how to read MSE and "
            "R squared, and the weak spots: outliers pull the line, and the relationship has to "
            "be roughly linear.",
            "seconds": 25,
        },
    ],
}

PYTHON = {
    "packages": ["numpy", "scikit-learn"],
    "dataset": "50 synthetic flats: size in m² and monthly rent in thousands of rupees, with "
    "random noise added to a true line (rent = 4 + 0.25 × size).",
    "steps": [
        {
            "title": "Make the data",
            "explanation": "A true line plus noise, with a fixed seed so everyone sees the same "
            "numbers.",
            "code": dedent(
                """\
                import numpy as np

                rng = np.random.default_rng(0)
                # 50 flats: size in square metres -> rent in thousands of rupees per month.
                size = rng.uniform(30, 120, 50)
                rent = 4 + 0.25 * size + rng.normal(0, 2.5, 50)
                print("First 3 flats:", [(int(round(s)), float(round(r, 1))) for s, r in zip(size[:3], rent[:3])])"""
            ),
        },
        {
            "title": "Least squares by hand",
            "explanation": "Slope = covariance / variance; the line passes through the mean point.",
            "code": dedent(
                """\
                # Least squares by hand: slope = cov(x, y) / var(x)
                w = np.sum((size - size.mean()) * (rent - rent.mean())) / np.sum((size - size.mean()) ** 2)
                b = rent.mean() - w * size.mean()
                print(f"By hand:       rent = {w:.3f} * size + {b:.2f}")"""
            ),
        },
        {
            "title": "Same thing with scikit-learn",
            "explanation": "scikit-learn expects a 2-D feature array, hence reshape(-1, 1).",
            "code": dedent(
                """\
                from sklearn.linear_model import LinearRegression

                model = LinearRegression().fit(size.reshape(-1, 1), rent)
                print(f"scikit-learn:  rent = {model.coef_[0]:.3f} * size + {model.intercept_:.2f}")"""
            ),
        },
        {
            "title": "Evaluate and predict",
            "explanation": "MSE is in squared units; R² is unit-free. Then predict an 80 m² flat.",
            "code": dedent(
                """\
                predicted = model.predict(size.reshape(-1, 1))
                mse = np.mean((rent - predicted) ** 2)
                r2 = model.score(size.reshape(-1, 1), rent)
                print(f"MSE = {mse:.2f}   R^2 = {r2:.3f}")
                print(f"Predicted rent for 80 m^2: {model.predict([[80]])[0]:.1f}k")"""
            ),
        },
    ],
    "expected_output": dedent(
        """\
        First 3 flats: [(87, 26.7), (54, 14.5), (34, 12.4)]
        By hand:       rent = 0.265 * size + 2.96
        scikit-learn:  rent = 0.265 * size + 2.96
        MSE = 6.21   R^2 = 0.886
        Predicted rent for 80 m^2: 24.1k"""
    ),
    "mistakes": [
        "Passing a 1-D array as X to scikit-learn (it needs shape (n, 1)).",
        "Judging fit by MSE alone without a baseline or R².",
        "Extrapolating far outside the range of the training data.",
        "Ignoring outliers that drag the fitted line.",
    ],
    "applications": [
        "Price and rent estimation",
        "Sales and demand forecasting baselines",
        "Quantifying the effect of one variable on another",
    ],
}

INTERVIEW = {
    "questions": [
        {
            "level": "basic",
            "kind": "conceptual",
            "question": "What is linear regression?",
            "answer": "A supervised method that predicts a continuous target as a linear "
            "combination of the features: ŷ = w·x + b (or ŷ = Xw + b with many features). It "
            "learns the weights that minimise the mean squared error between predictions and "
            "true values.",
            "interviewer_wants": "The equation, 'continuous target', and that it minimises "
            "squared error.",
            "follow_ups": [
                {
                    "question": "What does the slope mean in plain words?",
                    "answer": "How much the prediction changes for a one-unit increase in that "
                    "feature, holding other features fixed.",
                }
            ],
            "origin": "ai_generated",
        },
        {
            "level": "basic",
            "kind": "math",
            "question": "Why do we minimise squared errors rather than plain errors?",
            "answer": "Plain errors can cancel out (positive and negative), so their sum can be "
            "zero for a bad line. Squaring keeps every error positive, penalises large errors "
            "more, and gives a smooth, convex loss with a unique minimum and a closed-form "
            "solution.",
            "interviewer_wants": "Cancellation, penalising big errors, and convexity.",
            "follow_ups": [
                {
                    "question": "What's a downside of squaring?",
                    "answer": "Outliers get huge weight. Mean absolute error or Huber loss are "
                    "more robust.",
                }
            ],
            "origin": "ai_generated",
        },
        {
            "level": "basic",
            "kind": "conceptual",
            "question": "What do MSE and R² tell you?",
            "answer": "MSE is the average squared residual, in squared units of the target; "
            "lower is better. R² is the share of the target's variance the model explains: 1 is "
            "perfect, 0 is no better than predicting the mean, and it can be negative for a "
            "model worse than the mean.",
            "interviewer_wants": "Correct interpretation of both, including R²'s baseline.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
        {
            "level": "intermediate",
            "kind": "math",
            "question": "Derive the slope of simple linear regression.",
            "answer": "Minimise Σ(yᵢ − w·xᵢ − b)². Setting the derivative with respect to b to "
            "zero gives b = ȳ − w·x̄. Substituting and setting the derivative with respect to w "
            "to zero gives w = Σ(xᵢ − x̄)(yᵢ − ȳ) / Σ(xᵢ − x̄)², i.e. cov(x, y) / var(x).",
            "interviewer_wants": "Partial derivatives set to zero and the covariance over "
            "variance result.",
            "follow_ups": [
                {
                    "question": "What's the matrix form?",
                    "answer": "w = (XᵀX)⁻¹Xᵀy, the normal equation, with a column of ones for "
                    "the intercept.",
                }
            ],
            "origin": "ai_generated",
        },
        {
            "level": "intermediate",
            "kind": "conceptual",
            "question": "What assumptions does linear regression make?",
            "answer": "A linear relationship between features and target; independent errors; "
            "constant error variance (homoscedasticity); and, for confidence intervals and "
            "p-values, roughly normal errors. Strongly correlated features (multicollinearity) "
            "make individual coefficients unstable.",
            "interviewer_wants": "Linearity, independence, homoscedasticity, normality for "
            "inference, and multicollinearity.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
        {
            "level": "intermediate",
            "kind": "scenario",
            "question": "When would you use gradient descent instead of the normal equation?",
            "answer": "When there are many features (inverting XᵀX costs about O(d³)), very "
            "large datasets that don't fit in memory, or streaming data. Gradient descent and "
            "its stochastic variants scale; the normal equation is exact and fast for small "
            "problems.",
            "interviewer_wants": "Computational cost reasoning, not just 'it's faster'.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
        {
            "level": "advanced",
            "kind": "conceptual",
            "question": "What are Ridge and Lasso, and when would you use them?",
            "answer": "Both add a penalty to the loss to shrink weights and reduce overfitting. "
            "Ridge adds λΣw², shrinking all weights smoothly and helping with "
            "multicollinearity. Lasso adds λΣ|w|, which can drive some weights exactly to zero, "
            "doing feature selection. Elastic Net mixes both.",
            "interviewer_wants": "L2 vs L1 penalties, shrinkage vs sparsity, and when each helps.",
            "follow_ups": [
                {
                    "question": "Why should features be scaled before regularising?",
                    "answer": "The penalty treats all weights equally, so features on larger "
                    "scales would be penalised unfairly.",
                }
            ],
            "origin": "ai_generated",
        },
        {
            "level": "advanced",
            "kind": "scenario",
            "question": "Your residual plot shows a curve. What does it mean and what do you do?",
            "answer": "The relationship isn't linear in the current features, so the model is "
            "systematically wrong in parts of the range. Add polynomial or transformed "
            "features (e.g. log), or use a non-linear model such as gradient-boosted trees.",
            "interviewer_wants": "Reading residual plots and fixing non-linearity.",
            "follow_ups": [],
            "origin": "ai_generated",
        },
    ],
    "takeaways": [
        "ŷ = w·x + b, fitted by minimising mean squared error.",
        "Slope = cov(x, y) / var(x) for one feature.",
        "MSE measures error; R² measures explained variance against the mean baseline.",
        "Outliers, non-linearity and multicollinearity are the classic pitfalls.",
    ],
}

QUIZ = {
    "questions": [
        {
            "difficulty": "easy",
            "kind": "concept",
            "prompt": "Linear regression predicts…",
            "options": ["A category", "A continuous number", "A cluster", "A probability only"],
            "answer": 1,
            "explanation": "It's a regression method: the output is a number.",
        },
        {
            "difficulty": "easy",
            "kind": "math",
            "prompt": "In ŷ = 0.25x + 4, what happens to ŷ when x goes up by 10?",
            "options": ["It rises by 0.25", "It rises by 2.5", "It rises by 4", "It doubles"],
            "answer": 1,
            "explanation": "The slope is 0.25 per unit, so 10 units add 2.5.",
        },
        {
            "difficulty": "medium",
            "kind": "concept",
            "prompt": "Why square the residuals in MSE?",
            "options": [
                "To make the numbers smaller",
                "So errors can't cancel out and big errors count more",
                "Because it's faster to compute",
                "To ignore outliers",
            ],
            "answer": 1,
            "explanation": "Squares are positive and grow quickly with the size of the error.",
        },
        {
            "difficulty": "medium",
            "kind": "math",
            "prompt": "An R² of 0 means the model…",
            "options": [
                "Is perfect",
                "Does no better than always predicting the mean",
                "Has zero error",
                "Is impossible to compute",
            ],
            "answer": 1,
            "explanation": "R² compares your model with the mean-only baseline.",
        },
        {
            "difficulty": "medium",
            "kind": "scenario",
            "prompt": "You add one extreme outlier to your data. The least-squares line…",
            "options": [
                "Doesn't change",
                "Moves toward the outlier",
                "Moves away from the outlier",
                "Becomes horizontal",
            ],
            "answer": 1,
            "explanation": "Squared error gives the outlier a large pull on the fit.",
        },
        {
            "difficulty": "hard",
            "kind": "code",
            "prompt": "Why does this raise an error?",
            "code": "model = LinearRegression()\nmodel.fit(size, rent)  # size is a 1-D array",
            "options": [
                "rent must be 2-D",
                "X must be 2-D: use size.reshape(-1, 1)",
                "LinearRegression needs a learning rate",
                "fit expects lists, not arrays",
            ],
            "answer": 1,
            "explanation": "scikit-learn expects features as a 2-D array of shape (samples, "
            "features).",
        },
        {
            "difficulty": "hard",
            "kind": "concept",
            "prompt": "Which penalty can set some weights exactly to zero?",
            "options": ["Ridge (L2)", "Lasso (L1)", "Neither", "Both equally"],
            "answer": 1,
            "explanation": "The L1 penalty's corners drive some coefficients to exactly zero.",
        },
    ]
}

REVISION = {
    "definitions": [
        {
            "term": "Linear regression",
            "meaning": "Predicts a number as a weighted sum of features plus a bias.",
        },
        {"term": "Residual", "meaning": "y − ŷ: how far a prediction misses."},
        {"term": "MSE", "meaning": "Average of squared residuals; lower is better."},
        {"term": "R²", "meaning": "Share of variance explained; 1 perfect, 0 = mean baseline."},
        {"term": "Regularisation", "meaning": "A penalty on weight size to reduce overfitting."},
    ],
    "formulas": [
        {"name": "Model", "expression": "ŷ = w·x + b", "meaning": "Slope w, intercept b."},
        {"name": "MSE", "expression": "(1/n) Σ (yᵢ − ŷᵢ)²", "meaning": "Mean squared error."},
        {
            "name": "Slope",
            "expression": "w = cov(x, y) / var(x)",
            "meaning": "Least-squares slope for one feature.",
        },
        {
            "name": "Normal equation",
            "expression": "w = (XᵀX)⁻¹Xᵀy",
            "meaning": "Closed-form solution for many features.",
        },
    ],
    "comparison": {
        "title": "Ridge vs Lasso",
        "columns": ["", "Ridge (L2)", "Lasso (L1)"],
        "rows": [
            ["Penalty", "λΣw²", "λΣ|w|"],
            ["Effect", "Shrinks all weights", "Can zero some weights"],
            ["Good for", "Correlated features", "Feature selection"],
        ],
    },
    "mistakes": [
        "Extrapolating far beyond the data's range.",
        "Ignoring outliers and curved residual patterns.",
        "Regularising without scaling features.",
    ],
    "confusions": [
        {
            "pair": "MSE vs R²",
            "difference": "MSE is an error in squared units; R² is a unit-free share of explained variance.",
        },
    ],
    "takeaways": [
        "Fit = minimise squared error.",
        "Check residuals, not just one number.",
        "Use Ridge/Lasso when overfitting or with many features.",
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
