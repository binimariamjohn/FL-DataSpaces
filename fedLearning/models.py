import numpy as np
import pickle
import tensorflow as tf

def create_and_compile_model(input_shape=(28, 28, 1), learning_rate=0.01):
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=input_shape),
        tf.keras.layers.Conv2D(20, kernel_size=5, activation='relu', padding='valid'),
        tf.keras.layers.MaxPooling2D(pool_size=(2, 2)),
        tf.keras.layers.Conv2D(50, kernel_size=5, activation='relu', padding='valid'),
        tf.keras.layers.MaxPooling2D(pool_size=(2, 2)),
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(500, activation='relu'),
        tf.keras.layers.Dense(10)
    ])
    model.compile(
        optimizer=tf.keras.optimizers.SGD(learning_rate=learning_rate, momentum=0.9),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=['accuracy']
    )
    return model

# Convert model weights from numpy arrays to nested  (HTTP transfer)
def serialize_weights(model_or_weights):
    if hasattr(model_or_weights, 'get_weights'):
        weights = model_or_weights.get_weights()
    else:
        weights = model_or_weights
    return [w.tolist() if isinstance(w, np.ndarray) else w for w in weights]

# Convert weight lists back from JSON format to numpy
def deserialize_weights(serialized_weights):
    return [np.array(w, dtype=np.float32) for w in serialized_weights]

# Load pickled model weights from file (used for EDC Nextcloud downloads)
def load_weights_from_file(file_path):
    with open(file_path, 'rb') as f:
        return pickle.load(f)

# Calculate byte size of weights in pickle format
def get_weights_size(weights):
    return len(pickle.dumps(weights, protocol=pickle.HIGHEST_PROTOCOL))