import numpy as np
import pandas as pd
from scipy.io import arff
from sklearn.preprocessing import PowerTransformer

from simplegan import SimpleGan

data = arff.loadarff("diabetes.arff")
data = pd.DataFrame(data[0])

scaled_data = data.copy().reset_index(drop=True)
scaled_data = pd.get_dummies(scaled_data, prefix_sep='class_col', drop_first=True)
class_col = [col for col in scaled_data.columns if 'class_col' in col]
num_col = [col for col in scaled_data.columns if col not in class_col]
binary_col = [col for col in num_col if len(scaled_data[col].unique()) == 2]

# Remove all the binary columns
[num_col.remove(col) for col in binary_col]

data_transformer = PowerTransformer(method='yeo-johnson', standardize=True, copy=True)
scaled_data[num_col] = data_transformer.fit_transform(scaled_data[num_col])
scaled_data = pd.get_dummies(scaled_data, prefix="binary", columns=binary_col, drop_first=True)

# Define the GAN and training parameters
noise_dim = 64
layer_dim = 512
batch_size = 64
epochs = 1 + 199
learning_rate = 1e-4
save_dir = 'weight_cache_simple_dataset1'

# Training the GAN model chosen: Vanilla GAN, CGAN, DCGAN, etc.
simple_gan = SimpleGan(batch_size=batch_size,
                       learning_rate=learning_rate,
                       noise_dim=noise_dim,
                       data_shape=scaled_data.shape,
                       layers_dim=layer_dim)
simple_gan.train(scaled_data, epochs, save_dir)

gen_model = simple_gan.generator
df_generated_data = pd.DataFrame(simple_gan.generator.predict(np.random.normal(size=(100, noise_dim))),
                                 columns=scaled_data.columns)
df_generated_data.to_csv(f'./{save_dir}/df_generated_data_scaled.csv')

predict_generated_data = simple_gan.discriminator.predict([df_generated_data])
np.save(f'./{save_dir}/predict_generated_data.npy', np.array(predict_generated_data))

print(f"We faked {sum(predict_generated_data > 0.5)} out of 100")
df_generated_data[num_col] = data_transformer.inverse_transform(df_generated_data[num_col])
df_generated_data.to_csv(f'./{save_dir}/df_generated_data.csv')
print(df_generated_data.head(20))
