# -*- coding: utf-8 -*-
"""GRU LSTM RNN ANN 03.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1hY80wt2zz2dfNFRou3QdJofPTy35qjgS

# **IMPORT LIBRARIES**
"""

import pandas as pd
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
import seaborn as sns
plt.rcParams["figure.figsize"] = (12,5)
import warnings
warnings.filterwarnings('ignore')
from sklearn.metrics import mean_squared_error, explained_variance_score, max_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import RobustScaler

"""# **LOAD DATA**"""

# Import the CSV file
df = pd.read_csv("/content/busan_dataset.csv")
df.head()

# Remove spaces on the column
df.columns = df.columns.str.lstrip()
df.columns = df.columns.str.rstrip()

# Parse the "Date" column
df['Date'] = pd.to_datetime(df['Date'])
df.set_index('Date', inplace=True)

"""# **DATA EXPLORATION**"""

df.shape
df.info()

df.head()

df.describe()

# Check null value
df.isna().sum()

# fill the nan values by upper row value
#df = df.fillna(method='ffill')
#df.tail()

"""# **DATA ENGINEERING**"""

# Extracting features from the index before filtering the DataFrame
df['hour'] = df.index.hour
df['month'] = df.index.month

# Now filter the DataFrame to include only the required columns and the new features
required_cols = ['GHI_Average', 'SunZenith_KMU', 'Ambient_Pressure', 'Water', 'AOD', 'wv_500', 'CI_Beyer', 'hour', 'month']
df = df[required_cols]

# Display the first few rows to confirm the columns are present
print(df.head())

sns.lineplot(x=df.index, y='GHI_Average', data=df)
plt.show()

df_by_month = df.resample('M').sum()
sns.lineplot(x=df_by_month.index, y='GHI_Average', data=df_by_month)
plt.show()

# Create a figure with 4 subplots (2 rows, 2 columns)
fig, axs = plt.subplots(2, figsize=(18, 6))

# Ensure that axs is a flat array, in case it isn't already
if isinstance(axs, np.ndarray):
    axs = axs.flatten()

# Plot 1: Hourly GHI Average
sns.pointplot(x='hour', y='GHI_Average', data=df, ax=axs[0])
axs[0].set_title('Hourly GHI Average')

# Plot 2: GHI Average by Month
sns.pointplot(x='month', y='GHI_Average', data=df, ax=axs[1])
axs[1].set_title('GHI Average by Month')

# Show the plots
plt.tight_layout()
plt.show()

"""# **DATA PREPROCESSING**

Split Data into 70% training, 15% test, and 15% validation
"""

# Define split ratios
train_ratio = 0.7
test_ratio = 0.15
validation_ratio = 0.15

# Calculate the sizes of each set
train_size = int(len(df) * train_ratio)
test_size = int(len(df) * test_ratio)
validation_size = len(df) - train_size - test_size  # Remaining data for validation

# Split the dataset
train = df.iloc[:train_size]
test = df.iloc[train_size:train_size + test_size]
validation = df.iloc[train_size + test_size:]

# Print the sizes of each set
print('Train size:', len(train))
print('Test size:', len(test))
print('Validation size:', len(validation))

# Input Scaling
cols = ['SunZenith_KMU', 'Ambient_Pressure', 'Water', 'AOD', 'wv_500', 'CI_Beyer', 'hour', 'month']

scaler = RobustScaler()
scaler = scaler.fit(np.asarray(train[cols]))

train.loc[:, cols] = scaler.transform(np.asarray(train[cols]))
test.loc[:, cols] = scaler.transform(np.asarray(test[cols]))

# scaling GHI
GHI_scaler = RobustScaler()
GHI_scaler = GHI_scaler.fit(train[['GHI_Average']])
train['GHI_Average'] = GHI_scaler.transform(train[['GHI_Average']])
test['GHI_Average'] = GHI_scaler.transform(test[['GHI_Average']])

print('Train shape:',train.shape)
print('Test shape:', test.shape)

"""# **MODEL BUILDING**"""

def create_dataset(X, y, time_steps=1):
    Xs, ys = [], []
    for i in range(len(X) - time_steps):
        v = X.iloc[i:(i + time_steps)].values
        Xs.append(v)
        ys.append(y.iloc[i + time_steps])
    return np.array(Xs), np.array(ys)

time_steps = 7
# reshape to [samples, time_steps, features]
X_train, y_train = create_dataset(train, train.GHI_Average, time_steps)
X_test, y_test = create_dataset(test, test.GHI_Average, time_steps)
print(X_train.shape, y_train.shape)

"""# **GRU**"""

# GRU model design

gru_model = tf.keras.Sequential()
gru_model.add(tf.keras.layers.GRU(units=100, input_shape=(X_train.shape[1], X_train.shape[2])))
gru_model.add(tf.keras.layers.Dropout(rate=0.5))
gru_model.add(tf.keras.layers.Dense(units=1))
gru_model.compile(loss='mean_squared_error', optimizer='adam')
gru_model.summary()

gru_history = gru_model.fit(X_train, y_train,epochs=100,batch_size=64,validation_split=0.15,shuffle=False)

# history plotting
plt.plot(gru_history.history['loss'], label='train')
plt.plot(gru_history.history['val_loss'], label='validation')
plt.title('GRU model loss')
plt.ylabel('loss')
plt.xlabel('epoch')
plt.legend()
plt.show()

# inverse scaling

y_pred_GRU = gru_model.predict(X_test)
y_train_inv = GHI_scaler.inverse_transform(y_train.reshape(1, -1))
y_test_inv = GHI_scaler.inverse_transform(y_test.reshape(1, -1))
y_pred_GRU_inv = GHI_scaler.inverse_transform(y_pred_GRU)

# visualizing predicition
plt.plot(y_test_inv.flatten(), marker='.', label='true')
plt.plot(y_pred_GRU_inv.flatten(), 'r', label='predicted')
plt.title('GRU model prediction')
plt.ylabel('GHI')
plt.xlabel('time')
plt.legend()
plt.show()

#evaluation metrics
from sklearn.metrics import mean_squared_error
from math import sqrt
from sklearn.metrics import r2_score
from sklearn.metrics import mean_absolute_error

def gru_accuracy_metrics(y_test_inv, y_pred_LSTM_inv):
    # Flatten the arrays
    y_test_flat = y_test_inv.flatten()
    y_pred_GRU_flat = y_pred_GRU_inv.flatten()

    # Compute the differences
    diff = y_test_flat - y_pred_GRU_flat

    # Compute metrics
    r2 = r2_score(y_test_flat, y_pred_GRU_flat)
    mae = mean_absolute_error(y_test_flat, y_pred_GRU_flat)
    mse = mean_squared_error(y_test_flat, y_pred_GRU_flat)
    rmse = np.sqrt(mse)
    mbe = np.mean(diff)
    rrmse = rmse / np.mean(y_test_flat)
    rmbe = mbe / np.mean(y_test_flat)

    # Print the grouped metrics
    print("\nGRU Accuracy Metrics")
    print("-------------------")
    print(f'R^2: {r2:.4f}')
    print(f'MAE: {mae:.4f}')
    print(f'MSE: {mse:.4f}')
    print(f'RMSE: {rmse:.4f}')
    print(f'MBE: {mbe:.4f}')
    print(f'RRMSE: {rrmse:.4f}')
    print(f'RMBE: {rmbe:.4f}')

# Call the function to compute and print GRU Accuracy Metrics
gru_accuracy_metrics(y_test_inv, y_pred_GRU_inv)

"""# **LSTM**"""

# LSTM model building
lstm_model = tf.keras.Sequential()
lstm_model.add(tf.keras.layers.LSTM(units=100, input_shape=(X_train.shape[1], X_train.shape[2])))
lstm_model.add(tf.keras.layers.Dropout(rate=0.5))
lstm_model.add(tf.keras.layers.Dense(units=1))
lstm_model.compile(loss='mse', optimizer='adam')

lstm_history = lstm_model.fit(X_train, y_train,epochs=100,batch_size=64,validation_split=0.15,shuffle=False)

lstm_model.summary()

# model validation
plt.plot(lstm_history.history['loss'], label='train')
plt.plot(lstm_history.history['val_loss'], label='validation')
plt.title('LSTM model loss')
plt.ylabel('loss')
plt.xlabel('epoch')
plt.legend()
plt.show()

# inverse scaling

y_pred_LSTM = lstm_model.predict(X_test)
y_train_inv = GHI_scaler.inverse_transform(y_train.reshape(1, -1))
y_test_inv = GHI_scaler.inverse_transform(y_test.reshape(1, -1))
y_pred_LSTM_inv = GHI_scaler.inverse_transform(y_pred_LSTM)

# visualize prediction
plt.plot(y_test_inv.flatten(), marker='.', label='true')
plt.plot(y_pred_LSTM_inv.flatten(), 'r', label='predicted')
plt.title('LSTM model prediction')
plt.ylabel('GHI')
plt.xlabel('time')
plt.legend()
plt.show()

def LSTM_accuracy_metrics(y_test_inv, y_pred_LSTM_inv):
    # Flatten the arrays
    y_test_flat = y_test_inv.flatten()
    y_pred_LSTM_flat = y_pred_LSTM_inv.flatten()

    # Compute the differences
    diff = y_test_flat - y_pred_LSTM_flat

    # Compute metrics
    r2 = r2_score(y_test_flat, y_pred_LSTM_flat)
    mae = mean_absolute_error(y_test_flat, y_pred_LSTM_flat)
    mse = mean_squared_error(y_test_flat, y_pred_LSTM_flat)
    rmse = np.sqrt(mse)
    mbe = np.mean(diff)
    rrmse = rmse / np.mean(y_test_flat)
    rmbe = mbe / np.mean(y_test_flat)

    # Print the grouped metrics
    print("\nLSTM Accuracy Metrics")
    print("-------------------")
    print(f'R^2: {r2:.4f}')
    print(f'MAE: {mae:.4f}')
    print(f'MSE: {mse:.4f}')
    print(f'RMSE: {rmse:.4f}')
    print(f'MBE: {mbe:.4f}')
    print(f'RRMSE: {rrmse:.4f}')
    print(f'RMBE: {rmbe:.4f}')

# Call the function to compute and print GRU Accuracy Metrics
LSTM_accuracy_metrics(y_test_inv, y_pred_LSTM_inv)

"""# **RNN**"""

# RNN model building
rnn_model = tf.keras.Sequential()
rnn_model.add(tf.keras.layers.SimpleRNN(units=100, activation='relu', input_shape=(time_steps, X_train.shape[2])))
rnn_model.add(tf.keras.layers.Dropout(rate=0.5))
rnn_model.add(tf.keras.layers.Dense(units=1))
rnn_model.compile(loss='mse', optimizer='adam')

# Train the model
rnn_history = rnn_model.fit(X_train, y_train, epochs=100, batch_size=64, validation_split=0.15, shuffle=False)

# Model summary
rnn_model.summary()

# model validation
plt.plot(rnn_history.history['loss'], label='train')
plt.plot(rnn_history.history['val_loss'], label='validation')
plt.title('RNN model loss')
plt.ylabel('loss')
plt.xlabel('epoch')
plt.legend()
plt.show()

# Inverse scaling
y_pred_RNN = rnn_model.predict(X_test)
y_train_inv = GHI_scaler.inverse_transform(y_train.reshape(1, -1))
y_test_inv = GHI_scaler.inverse_transform(y_test.reshape(1, -1))
y_pred_RNN_inv = GHI_scaler.inverse_transform(y_pred_RNN)

# visualize prediction
plt.plot(y_test_inv.flatten(), marker='.', label='true')
plt.plot(y_pred_RNN_inv.flatten(), 'r', label='predicted')
plt.title('RNN model prediction')
plt.ylabel('GHI')
plt.xlabel('time')
plt.legend()
plt.show()

def RNN_accuracy_metrics(y_test_inv, y_pred_RNN_inv):
    # Flatten the arrays
    y_test_flat = y_test_inv.flatten()
    y_pred_RNN_flat = y_pred_RNN_inv.flatten()

    # Compute the differences
    diff = y_test_flat - y_pred_RNN_flat

    # Compute metrics
    r2 = r2_score(y_test_flat, y_pred_RNN_flat)
    mae = mean_absolute_error(y_test_flat, y_pred_RNN_flat)
    mse = mean_squared_error(y_test_flat, y_pred_RNN_flat)
    rmse = np.sqrt(mse)
    mbe = np.mean(diff)
    rrmse = rmse / np.mean(y_test_flat)
    rmbe = mbe / np.mean(y_test_flat)

    # Print the grouped metrics
    print("\nRNN Accuracy Metrics")
    print("-------------------")
    print(f'R^2: {r2:.4f}')
    print(f'MAE: {mae:.4f}')
    print(f'MSE: {mse:.4f}')
    print(f'RMSE: {rmse:.4f}')
    print(f'MBE: {mbe:.4f}')
    print(f'RRMSE: {rrmse:.4f}')
    print(f'RMBE: {rmbe:.4f}')

# Call the function to compute and print RNN Accuracy Metrics
RNN_accuracy_metrics(y_test_inv, y_pred_RNN_inv)

"""# **ANN**"""

import numpy as np
import tensorflow as tf

# Create a separate copy of the dataset for ANN
ann_train = train.copy()
ann_test = test.copy()

# Function to flatten and reshape the data for ANN input
def create_ann_dataset(X, y, time_steps=1):
    Xs, ys = [], []
    for i in range(len(X) - time_steps):
        v = X.iloc[i:(i + time_steps)].values
        Xs.append(v.flatten())  # Flatten the input for ANN
        ys.append(y.iloc[i + time_steps])
    return np.array(Xs), np.array(ys)

time_steps = 7

# Use the copied datasets to flatten and reshape for ANN
X_ANN_train, y_ANN_train = create_ann_dataset(ann_train, ann_train['GHI_Average'], time_steps)
X_ANN_test, y_ANN_test = create_ann_dataset(ann_test, ann_test['GHI_Average'], time_steps)

print("X_ANN_train shape:", X_ANN_train.shape)
print("y_ANN_train shape:", y_ANN_train.shape)
print("X_ANN_test shape:", X_ANN_test.shape)
print("y_ANN_test shape:", y_ANN_test.shape)

# ANN model design
ann_model = tf.keras.Sequential()
ann_model.add(tf.keras.layers.Dense(units=100, activation='relu', input_shape=(X_ANN_train.shape[1],)))  # Flattened input
ann_model.add(tf.keras.layers.Dropout(rate=0.5))
ann_model.add(tf.keras.layers.Dense(units=1))
ann_model.compile(loss='mean_squared_error', optimizer='adam')
ann_model.summary()

# Train the model
ann_history = ann_model.fit(X_ANN_train, y_ANN_train, epochs=100, batch_size=64, validation_split=0.15, shuffle=False)

# model validation
plt.plot(ann_history.history['loss'], label='train')
plt.plot(ann_history.history['val_loss'], label='validation')
plt.title('ANN model loss')
plt.ylabel('loss')
plt.xlabel('epoch')
plt.legend()
plt.show()

# Inverse scaling for the predicted values
y_pred_ANN = ann_model.predict(X_ANN_test)
y_pred_ANN_reshaped = y_pred_ANN.reshape(-1, 1)

y_ANN_train_inv = GHI_scaler.inverse_transform(y_ANN_train.reshape(-1, 1))
y_ANN_test_inv = GHI_scaler.inverse_transform(y_ANN_test.reshape(-1, 1))
y_pred_ANN_inv = GHI_scaler.inverse_transform(y_pred_ANN_reshaped)

# Visualize prediction
plt.plot(y_ANN_test_inv.flatten(), marker='.', label='true')
plt.plot(y_pred_ANN_inv.flatten(), 'r', label='predicted')
plt.title('ANN model prediction')
plt.ylabel('GHI')
plt.xlabel('time')
plt.legend()
plt.show()

def ANN_accuracy_metrics(y_ANN_test_inv, y_pred_ANN_inv):
    # Flatten the arrays
    y_ANN_test_flat = y_ANN_test_inv.flatten()
    y_pred_ANN_flat = y_pred_ANN_inv.flatten()

    # Compute the differences
    diff = y_ANN_test_flat - y_pred_ANN_flat

    # Compute metrics
    r2 = r2_score(y_ANN_test_flat, y_pred_ANN_flat)
    mae = mean_absolute_error(y_ANN_test_flat, y_pred_ANN_flat)
    mse = mean_squared_error(y_ANN_test_flat, y_pred_ANN_flat)
    rmse = np.sqrt(mse)
    mbe = np.mean(diff)
    rrmse = rmse / np.mean(y_ANN_test_flat)
    rmbe = mbe / np.mean(y_ANN_test_flat)

    # Print the grouped metrics
    print("\nANN Accuracy Metrics")
    print("-------------------")
    print(f'R^2: {r2:.4f}')
    print(f'MAE: {mae:.4f}')
    print(f'MSE: {mse:.4f}')
    print(f'RMSE: {rmse:.4f}')
    print(f'MBE: {mbe:.4f}')
    print(f'RRMSE: {rrmse:.4f}')
    print(f'RMBE: {rmbe:.4f}')

# Call the function to compute and print ANN Accuracy Metrics
ANN_accuracy_metrics(y_ANN_test_inv, y_pred_ANN_inv)

"""# **CNN**"""

# CNN model building
cnn_model = tf.keras.Sequential()

# Add a Conv1D layer (filters = 64, kernel_size = 3, activation = relu)
cnn_model.add(tf.keras.layers.Conv1D(filters=64, kernel_size=3, activation='relu', input_shape=(X_train.shape[1], X_train.shape[2])))

# Add a MaxPooling1D layer to downsample the input
cnn_model.add(tf.keras.layers.MaxPooling1D(pool_size=2))

# Add a Dropout layer to prevent overfitting
cnn_model.add(tf.keras.layers.Dropout(rate=0.5))

# Add a Flatten layer to reshape the output for Dense layers
cnn_model.add(tf.keras.layers.Flatten())

# Add a Dense layer for the output
cnn_model.add(tf.keras.layers.Dense(units=1))

# Compile the CNN model
cnn_model.compile(loss='mse', optimizer='adam')

# Train the CNN model
cnn_history = cnn_model.fit(X_train, y_train, epochs=100, batch_size=64, validation_split=0.15, shuffle=False)

# Model summary
cnn_model.summary()

# Model validation (loss plot)
plt.plot(cnn_history.history['loss'], label='train')
plt.plot(cnn_history.history['val_loss'], label='validation')
plt.title('CNN model loss')
plt.ylabel('loss')
plt.xlabel('epoch')
plt.legend()
plt.show()

# Predict using the trained CNN model
y_pred_CNN = cnn_model.predict(X_test)

# Inverse scaling
y_train_inv = GHI_scaler.inverse_transform(y_train.reshape(1, -1))
y_test_inv = GHI_scaler.inverse_transform(y_test.reshape(1, -1))
y_pred_CNN_inv = GHI_scaler.inverse_transform(y_pred_CNN)

# Visualize the prediction
plt.plot(y_test_inv.flatten(), marker='.', label='true')
plt.plot(y_pred_CNN_inv.flatten(), 'r', label='predicted')
plt.title('CNN model prediction')
plt.ylabel('GHI')
plt.xlabel('time')
plt.legend()
plt.show()

def CNN_accuracy_metrics(y_test_inv, y_pred_CNN_inv):
    # Flatten the arrays
    y_test_flat = y_test_inv.flatten()
    y_pred_CNN_flat = y_pred_CNN_inv.flatten()

    # Compute the differences
    diff = y_test_flat - y_pred_CNN_flat

    # Compute metrics
    r2 = r2_score(y_test_flat, y_pred_CNN_flat)
    mae = mean_absolute_error(y_test_flat, y_pred_CNN_flat)
    mse = mean_squared_error(y_test_flat, y_pred_CNN_flat)
    rmse = np.sqrt(mse)
    mbe = np.mean(diff)
    rrmse = rmse / np.mean(y_test_flat)
    rmbe = mbe / np.mean(y_test_flat)

    # Print the grouped metrics
    print("\nCNN Accuracy Metrics")
    print("-------------------")
    print(f'R^2: {r2:.4f}')
    print(f'MAE: {mae:.4f}')
    print(f'MSE: {mse:.4f}')
    print(f'RMSE: {rmse:.4f}')
    print(f'MBE: {mbe:.4f}')
    print(f'RRMSE: {rrmse:.4f}')
    print(f'RMBE: {rmbe:.4f}')

# Call the function to compute and print CNN Accuracy Metrics
CNN_accuracy_metrics(y_test_inv, y_pred_CNN_inv)

"""# **MLP**"""

import numpy as np

# Flatten the input data for MLP
X_train_flat = X_train.reshape(X_train.shape[0], -1).copy()  # Flatten and make a copy
X_test_flat = X_test.reshape(X_test.shape[0], -1).copy()    # Flatten and make a copy

# MLP model building
mlp_model = tf.keras.Sequential()
mlp_model.add(tf.keras.layers.Dense(units=100, activation='relu', input_shape=(X_train_flat.shape[1],)))  # Change input shape to (63,)
mlp_model.add(tf.keras.layers.Dropout(rate=0.5))
mlp_model.add(tf.keras.layers.Dense(units=1))  # Output layer
mlp_model.compile(loss='mse', optimizer='adam')

# Train the model
mlp_history = mlp_model.fit(X_train_flat, y_train, epochs=100, batch_size=64, validation_split=0.15, shuffle=False)

# Model summary
mlp_model.summary()

# Model validation
plt.plot(mlp_history.history['loss'], label='train')
plt.plot(mlp_history.history['val_loss'], label='validation')
plt.title('MLP model loss')
plt.ylabel('loss')
plt.xlabel('epoch')
plt.legend()
plt.show()

# Make predictions with the flattened test data
y_pred_MLP = mlp_model.predict(X_test_flat)

# Inverse scaling for MLP predictions
y_train_inv = GHI_scaler.inverse_transform(y_train.reshape(1, -1))
y_test_inv = GHI_scaler.inverse_transform(y_test.reshape(1, -1))
y_pred_MLP_inv = GHI_scaler.inverse_transform(y_pred_MLP)

# Visualize prediction
plt.plot(y_test_inv.flatten(), marker='.', label='true')
plt.plot(y_pred_MLP_inv.flatten(), 'r', label='predicted')
plt.title('MLP model prediction')
plt.ylabel('GHI')
plt.xlabel('time')
plt.legend()
plt.show()

def MLP_accuracy_metrics(y_test_inv, y_pred_MLP_inv):
    # Flatten the arrays
    y_test_flat = y_test_inv.flatten()
    y_pred_MLP_flat = y_pred_MLP_inv.flatten()

    # Compute the differences
    diff = y_test_flat - y_pred_MLP_flat

    # Compute metrics
    r2 = r2_score(y_test_flat, y_pred_MLP_flat)
    mae = mean_absolute_error(y_test_flat, y_pred_MLP_flat)
    mse = mean_squared_error(y_test_flat, y_pred_MLP_flat)
    rmse = np.sqrt(mse)
    mbe = np.mean(diff)
    rrmse = rmse / np.mean(y_test_flat)
    rmbe = mbe / np.mean(y_test_flat)

    # Print the grouped metrics
    print("\nMLP Accuracy Metrics")
    print("-------------------")
    print(f'R^2: {r2:.4f}')
    print(f'MAE: {mae:.4f}')
    print(f'MSE: {mse:.4f}')
    print(f'RMSE: {rmse:.4f}')
    print(f'MBE: {mbe:.4f}')
    print(f'RRMSE: {rrmse:.4f}')
    print(f'RMBE: {rmbe:.4f}')

# Call the function to compute and print MLP Accuracy Metrics
MLP_accuracy_metrics(y_test_inv, y_pred_MLP_inv)

"""# **SVR**"""

from sklearn.svm import SVR
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, r2_score
import matplotlib.pyplot as plt
import numpy as np

# Flatten X_train and X_test to be 2D arrays for SVR
X_train_flat = X_train.reshape(X_train.shape[0], -1).copy()
X_test_flat = X_test.reshape(X_test.shape[0], -1).copy()

# Initialize the SVR model
svr_model = SVR(kernel='rbf', C=100, gamma=0.1, epsilon=0.1)

# Train the SVR model
svr_model.fit(X_train_flat, y_train)

# Predict using the SVR model
y_pred_SVR = svr_model.predict(X_test_flat)

# Inverse scaling of predictions
y_train_inv = GHI_scaler.inverse_transform(y_train.reshape(-1, 1))
y_test_inv = GHI_scaler.inverse_transform(y_test.reshape(-1, 1))
y_pred_SVR_inv = GHI_scaler.inverse_transform(y_pred_SVR.reshape(-1, 1))

# Visualize the prediction
plt.plot(y_test_inv.flatten(), marker='.', label='true')
plt.plot(y_pred_SVR_inv.flatten(), 'r', label='predicted')
plt.title('SVR model prediction')
plt.ylabel('GHI')
plt.xlabel('time')
plt.legend()
plt.show()

def SVR_accuracy_metrics(y_test_inv, y_pred_SVR_inv):
    # Flatten the arrays
    y_test_flat = y_test_inv.flatten()
    y_pred_SVR_flat = y_pred_SVR_inv.flatten()

    # Compute the differences
    diff = y_test_flat - y_pred_SVR_flat

    # Compute metrics
    r2 = r2_score(y_test_flat, y_pred_SVR_flat)
    mae = mean_absolute_error(y_test_flat, y_pred_SVR_flat)
    mse = mean_squared_error(y_test_flat, y_pred_SVR_flat)
    rmse = np.sqrt(mse)
    mbe = np.mean(diff)
    rrmse = rmse / np.mean(y_test_flat)
    rmbe = mbe / np.mean(y_test_flat)

    # Print the grouped metrics
    print("\nSVR Accuracy Metrics")
    print("-------------------")
    print(f'R^2: {r2:.4f}')
    print(f'MAE: {mae:.4f}')
    print(f'MSE: {mse:.4f}')
    print(f'RMSE: {rmse:.4f}')
    print(f'MBE: {mbe:.4f}')
    print(f'RRMSE: {rrmse:.4f}')
    print(f'RMBE: {rmbe:.4f}')

# Call the function to compute and print SVR Accuracy Metrics
SVR_accuracy_metrics(y_test_inv, y_pred_SVR_inv)

"""# **DNN**"""

# Flatten X_train and X_test to be 2D arrays for DNN
X_train_flat = X_train.reshape(X_train.shape[0], -1)
X_test_flat = X_test.reshape(X_test.shape[0], -1)

# DNN model building
dnn_model = tf.keras.Sequential()
dnn_model.add(tf.keras.layers.Dense(units=100, activation='relu', input_shape=(X_train_flat.shape[1],)))
dnn_model.add(tf.keras.layers.Dropout(rate=0.5))
dnn_model.add(tf.keras.layers.Dense(units=1))  # Output layer
dnn_model.compile(loss='mse', optimizer='adam')

# Train the DNN model
dnn_history = dnn_model.fit(X_train_flat, y_train, epochs=100, batch_size=64, validation_split=0.15, shuffle=False)

# Model summary
dnn_model.summary()

# Plot model loss
plt.plot(dnn_history.history['loss'], label='train')
plt.plot(dnn_history.history['val_loss'], label='validation')
plt.title('DNN Model Loss')
plt.ylabel('Loss')
plt.xlabel('Epoch')
plt.legend()
plt.show()

# Inverse scaling
y_pred_DNN = dnn_model.predict(X_test_flat)
y_train_inv = GHI_scaler.inverse_transform(y_train.reshape(1, -1))
y_test_inv = GHI_scaler.inverse_transform(y_test.reshape(1, -1))
y_pred_DNN_inv = GHI_scaler.inverse_transform(y_pred_DNN)

# Visualize prediction
plt.plot(y_test_inv.flatten(), marker='.', label='True')
plt.plot(y_pred_DNN_inv.flatten(), 'r', label='Predicted')
plt.title('DNN Model Prediction')
plt.ylabel('GHI')
plt.xlabel('Time')
plt.legend()
plt.show()

def DNN_accuracy_metrics(y_test_inv, y_pred_DNN_inv):
    # Flatten the arrays
    y_test_flat = y_test_inv.flatten()
    y_pred_DNN_flat = y_pred_DNN_inv.flatten()

    # Compute the differences
    diff = y_test_flat - y_pred_DNN_flat

    # Compute metrics
    r2 = r2_score(y_test_flat, y_pred_DNN_flat)
    mae = mean_absolute_error(y_test_flat, y_pred_DNN_flat)
    mse = mean_squared_error(y_test_flat, y_pred_DNN_flat)
    rmse = np.sqrt(mse)
    mbe = np.mean(diff)
    rrmse = rmse / np.mean(y_test_flat)
    rmbe = mbe / np.mean(y_test_flat)

    # Print the grouped metrics
    print("\nDNN Accuracy Metrics")
    print("--------------------")
    print(f'R^2: {r2:.4f}')
    print(f'MAE: {mae:.4f}')
    print(f'MSE: {mse:.4f}')
    print(f'RMSE: {rmse:.4f}')
    print(f'MBE: {mbe:.4f}')
    print(f'RRMSE: {rrmse:.4f}')
    print(f'RMBE: {rmbe:.4f}')

# Call the function to compute and print DNN Accuracy Metrics
DNN_accuracy_metrics(y_test_inv, y_pred_DNN_inv)

"""# **MODEL COMPARISON**"""

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

def compute_metrics(y_true, y_pred):
    # Flatten the arrays
    y_true_flat = y_true.flatten()
    y_pred_flat = y_pred.flatten()

    # Compute the differences
    diff = y_true_flat - y_pred_flat

    # Compute metrics
    r2 = r2_score(y_true_flat, y_pred_flat)
    mae = mean_absolute_error(y_true_flat, y_pred_flat)
    mse = mean_squared_error(y_true_flat, y_pred_flat)
    rmse = np.sqrt(mse)
    mbe = np.mean(diff)

    return rmse, mae, mbe

def GRU_accuracy_metrics(y_test_inv, y_pred_GRU_inv):
    return compute_metrics(y_test_inv, y_pred_GRU_inv)

def LSTM_accuracy_metrics(y_test_inv, y_pred_LSTM_inv):
    return compute_metrics(y_test_inv, y_pred_LSTM_inv)

def RNN_accuracy_metrics(y_test_inv, y_pred_RNN_inv):
    return compute_metrics(y_test_inv, y_pred_RNN_inv)

def ANN_accuracy_metrics(y_ANN_test_inv, y_pred_ANN_inv):
    return compute_metrics(y_ANN_test_inv, y_pred_ANN_inv)

def CNN_accuracy_metrics(y_test_inv, y_pred_CNN_inv):
    return compute_metrics(y_test_inv, y_pred_CNN_inv)

def MLP_accuracy_metrics(y_test_inv, y_pred_MLP_inv):
    return compute_metrics(y_test_inv, y_pred_MLP_inv)

def SVR_accuracy_metrics(y_test_inv, y_pred_SVR_inv):
    return compute_metrics(y_test_inv, y_pred_SVR_inv)

def DNN_accuracy_metrics(y_test_inv, y_pred_DNN_inv):
    return compute_metrics(y_test_inv, y_pred_DNN_inv)

# Compute metrics for each model
rmse_GRU, mae_GRU, mbe_GRU = GRU_accuracy_metrics(y_test_inv, y_pred_GRU_inv)
rmse_LSTM, mae_LSTM, mbe_LSTM = LSTM_accuracy_metrics(y_test_inv, y_pred_LSTM_inv)
rmse_RNN, mae_RNN, mbe_RNN = RNN_accuracy_metrics(y_test_inv, y_pred_RNN_inv)
rmse_ANN, mae_ANN, mbe_ANN = ANN_accuracy_metrics(y_test_inv, y_pred_ANN_inv)
rmse_CNN, mae_CNN, mbe_CNN = CNN_accuracy_metrics(y_test_inv, y_pred_CNN_inv)
rmse_MLP, mae_MLP, mbe_MLP = MLP_accuracy_metrics(y_test_inv, y_pred_MLP_inv)
rmse_SVR, mae_SVR, mbe_SVR = SVR_accuracy_metrics(y_test_inv, y_pred_SVR_inv)
rmse_DNN, mae_DNN, mbe_DNN = DNN_accuracy_metrics(y_test_inv, y_pred_DNN_inv)

# Print or store the metrics as needed
print(f"GRU - RMSE: {rmse_GRU}, MAE: {mae_GRU}, MBE: {mbe_GRU}")
print(f"LSTM - RMSE: {rmse_LSTM}, MAE: {mae_LSTM}, MBE: {mbe_LSTM}")
print(f"RNN - RMSE: {rmse_RNN}, MAE: {mae_RNN}, MBE: {mbe_RNN}")
print(f"ANN - RMSE: {rmse_ANN}, MAE: {mae_ANN}, MBE: {mbe_ANN}")
print(f"CNN - RMSE: {rmse_CNN}, MAE: {mae_CNN}, MBE: {mbe_CNN}")
print(f"MLP - RMSE: {rmse_MLP}, MAE: {mae_MLP}, MBE: {mbe_MLP}")
print(f"SVR - RMSE: {rmse_SVR}, MAE: {mae_SVR}, MBE: {mbe_SVR}")
print(f"DNN - RMSE: {rmse_DNN}, MAE: {mae_DNN}, MBE: {mbe_DNN}")

# Create a DataFrame to compare the metrics
metrics_df = pd.DataFrame({
    'Model': ['GRU', 'LSTM', 'RNN', 'ANN', 'CNN', 'MLP', 'SVR', 'DNN'],
    'RMSE': [rmse_GRU, rmse_LSTM, rmse_RNN, rmse_ANN, rmse_CNN, rmse_MLP, rmse_SVR, rmse_DNN],
    'MAE': [mae_GRU, mae_LSTM, mae_RNN, mae_ANN, mae_CNN, mae_MLP, mae_SVR, mae_DNN],
    'MBE': [mbe_GRU, mbe_LSTM, mbe_RNN, mbe_ANN, mbe_CNN, mbe_MLP, mbe_SVR, mbe_DNN]
})

# Display the DataFrame
metrics_df

import matplotlib.pyplot as plt

# Define the custom color palette including a color for DNN
colors = ['#FF6347', '#4682B4', '#32CD32', '#FFD700', '#8A2BE2', '#FF1493', '#1E90FF', '#FF4500']  # Added color for DNN

# Create the bar graph
plt.figure(figsize=(19, 8))  # Adjust figure size to fit all bars

# Add grid (ruler)
plt.grid(axis='y', linestyle='--', alpha=0.7)  # Adds horizontal grid lines

# Create bars with the updated colors
bars = plt.bar(metrics_df['Model'], metrics_df['RMSE'], color=colors)

# Add labels on top of the bars
for bar in bars:
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2, yval + 1, round(yval, 2), ha='center', va='bottom')

plt.xlabel('Model')
plt.ylabel('RMSE')
plt.title('RMSE Comparison of Different Models')

# Set the bottom value of the y-axis to 105
plt.ylim(bottom=105)

# Show the plot
plt.show()

import matplotlib.pyplot as plt

# Number of data points to visualize
num_points = 75

# Extract the last 75 data points for actual values and model predictions
actual_values = y_test_inv.flatten()[-num_points:]
gru_pred = y_pred_GRU_inv.flatten()[-num_points:]
lstm_pred = y_pred_LSTM_inv.flatten()[-num_points:]
rnn_pred = y_pred_RNN_inv.flatten()[-num_points:]
ann_pred = y_pred_ANN_inv.flatten()[-num_points:]
cnn_pred = y_pred_CNN_inv.flatten()[-num_points:]
mlp_pred = y_pred_MLP_inv.flatten()[-num_points:]  # MLP predictions
svr_pred = y_pred_SVR_inv.flatten()[-num_points:]  # SVR predictions
dnn_pred = y_pred_DNN_inv.flatten()[-num_points:]  # Added DNN predictions

# Create a figure and axis
plt.figure(figsize=(14, 8))

# Plot the actual values with thicker line
plt.plot(actual_values, marker='.', label='Actual', color='black', linewidth=1.6)

# Plot predictions from different models with thinner lines
plt.plot(gru_pred, 'r', label='GRU Prediction', linewidth=0.7)
plt.plot(lstm_pred, 'g', label='LSTM Prediction', linewidth=0.7)
plt.plot(rnn_pred, 'b', label='RNN Prediction', linewidth=0.7)
plt.plot(ann_pred, 'm', label='ANN Prediction', linewidth=0.7)
plt.plot(cnn_pred, 'c', label='CNN Prediction', linewidth=0.7)
plt.plot(mlp_pred, 'orange', label='MLP Prediction', linewidth=0.7)  # MLP predictions
plt.plot(svr_pred, 'purple', label='SVR Prediction', linewidth=0.7)  # SVR predictions
plt.plot(dnn_pred, 'teal', label='DNN Prediction', linewidth=0.7)  # Added DNN predictions

# Add grid
plt.grid(True)

# Add titles and labels
plt.title('Comparison of Model Predictions with Actual Values')
plt.xlabel('Time')
plt.ylabel('GHI')
plt.legend()

# Show the plot
plt.show()