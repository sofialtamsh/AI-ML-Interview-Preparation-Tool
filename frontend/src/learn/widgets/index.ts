import type { ComponentType } from 'react'

import type { Widget } from '../../lib/types'
import { ActivationFunctions } from './ActivationFunctions'
import { GradientDescent } from './GradientDescent'
import { KMeans } from './KMeans'
import { KnnClassifier } from './KnnClassifier'
import { LinearRegression } from './LinearRegression'
import { NeuralNetwork } from './NeuralNetwork'

export const WIDGET_COMPONENTS: Record<Widget, ComponentType> = {
  knn_classifier: KnnClassifier,
  kmeans: KMeans,
  linear_regression: LinearRegression,
  neural_network: NeuralNetwork,
  activation_functions: ActivationFunctions,
  gradient_descent: GradientDescent,
}
