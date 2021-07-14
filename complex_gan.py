import os
from os import path

import numpy as np
import tensorflow as tf
from pandas import DataFrame
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from tensorflow.keras.layers import Input, Dense, Dropout
from tensorflow.keras.optimizers import Adam

TEST_SIZE = 0.3
LOSS = 'binary_crossentropy'
RANDOM_FOREST_PARAMS = {'n_estimators': 200,
                        'min_samples_split': 2,
                        'min_samples_leaf': 4,
                        'max_features': 'sqrt',
                        'max_depth': None,
                        'bootstrap': True}


class ComplexGAN:
    """
    A Simple Gan Implementation
    """

    def __init__(self, batch_size, learning_rate, noise_dim, data_shape, layers_dim):
        self.learning_rate = learning_rate
        self.noise_dim = noise_dim
        self.batch_size = batch_size
        self.data_x_shape = data_shape[0]
        self.data_y_shape = data_shape[1]
        self.layers_dim = layers_dim

        self.optimizer = Adam(self.learning_rate)

        self.generator = Generator(self.batch_size).build_model(input_shape=(self.noise_dim,),
                                                                dim=self.layers_dim,
                                                                data_dim=self.data_y_shape)

        self.discriminator = Discriminator(self.batch_size).build_model(input_shape=(self.data_y_shape,),
                                                                        dim=self.layers_dim)
        self.discriminator.compile(loss=LOSS,
                                   optimizer=self.optimizer,
                                   metrics=['accuracy'])



    def _create_combined_model(self):
        self.discriminator.trainable = False
        self.combined_model = CombinedModel(input=Input(shape=(self.noise_dim,)),
                                            generator=self.generator,
                                            discriminator=self.discriminator)
        self.combined_model.compile(loss=LOSS, optimizer=self.optimizer)

    def train(self, data, epochs):
        """
        Train the GAN
        """
        self._train_black_box_model(data)
        self._create_combined_model()



        valid = np.ones((self.batch_size, 1))
        fake = np.zeros((self.batch_size, 1))

        for epoch in range(epochs):
            batch_data = np.reshape(data.sample(n=self.batch_size).values, (self.batch_size, -1))
            noise = tf.random.normal((self.batch_size, self.noise_dim))

            # Generate data
            generated_data = self.generator(noise, training=True)

            # Train discriminator
            dis_loss_real_data = self.discriminator.train_on_batch(batch_data, valid)
            dis_loss_fake_data = self.discriminator.train_on_batch(generated_data, fake)
            dis_loss = np.average(dis_loss_real_data, dis_loss_fake_data)

            # Train generator
            for i in range(5):
                noise = tf.random.normal((self.batch_size, self.noise_dim))
                generator_loss = self.combined_model.train_on_batch(noise, valid)

            print("%d [Disc loss: %f, acc.: %.2f%%] [Gen loss: %f]" % (
                epoch, dis_loss[0], 100 * dis_loss[1], generator_loss))

        if not path.exists('weight_cache'):
            os.mkdir('weight_cache')

        h5_name = './weight_cache/' + '_{}_model_weights.h5'
        self.generator.save_weights(h5_name.format('generator'))
        self.discriminator.save_weights(h5_name.format('discriminator'))

    def _train_black_box_model(self, data: DataFrame):
        self.black_box = RandomForestRegressor(random_state=1, **RANDOM_FOREST_PARAMS)

        self.train_black_box, self.test_black_box = train_test_split(data, test_size=TEST_SIZE, random_state=1)

        self.X_train_black_box = self.train_black_box.drop('class')
        self.y_train_black_box = self.train_black_box['class']

        self.X_test_black_box = self.test_black_box.drop('class')
        self.y_test_black_box = self.test_black_box['class']

        self.black_box.fit(self.X_train_black_box, self.y_train_black_box)


class Generator(tf.keras.Model):
    """
    The Generator Model Class
    """

    def __init__(self, data_size, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_size = data_size

    def build_model(self, input_shape, dim, data_dim):
        input = Input(shape=input_shape, batch_size=self.data_size)
        x = Dense(dim, activation='relu')(input)
        x = Dense(dim * 2, activation='relu')(x)
        x = Dense(dim * 4, activation='relu')(x)
        x = Dense(data_dim)(x)
        return tf.keras.Model(inputs=input, outputs=x)


class Discriminator(tf.keras.Model):
    """
    The Discriminator Model Class
    """

    def __init__(self, data_size, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_size = data_size

    def build_model(self, input_shape, dim):
        input = Input(shape=input_shape, batch_size=self.data_size)
        x = Dense(dim * 4, activation='relu')(input)
        x = Dropout(0.1)(x)
        x = Dense(dim * 2, activation='relu')(x)
        x = Dropout(0.1)(x)
        x = Dense(dim, activation='relu')(x)
        x = Dense(1, activation='sigmoid')(x)
        return tf.keras.Model(inputs=input, outputs=x)


class CombinedModel(tf.keras.Model):
    """
    The Combined Model
    """

    def __init__(self, input, generator, discriminator):
        record = generator(input)
        discriminator.trainable = False
        super().__init__(input, discriminator(record))
