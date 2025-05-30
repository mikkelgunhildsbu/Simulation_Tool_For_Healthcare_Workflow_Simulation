import ast
import numpy as np
import matplotlib.pyplot as plt
plt.switch_backend('TkAgg')
import pandas as pd
import joblib
import ast
from sklearn.tree import DecisionTreeRegressor, plot_tree, DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error, accuracy_score

"""
Implementation of decision for case splitting using specimen type and number of specimen containers as features. 
"""

blocks = pd.read_csv('blocks.csv')

X = blocks[['specimen_containers', 'specimen_typ']]
y = blocks['num_blocs']

X_encoded = pd.get_dummies(X, columns=['specimen_typ'], drop_first=False)


X_train, X_test, y_train, y_test = train_test_split(
    X_encoded, y, test_size=0.3, random_state=42
)

reg = DecisionTreeRegressor(random_state=33)
reg.fit(X_train, y_train)

y_pred_float = reg.predict(X_test)
y_pred = np.rint(y_pred_float).astype(int)

mse = mean_squared_error(y_test, y_pred)
mae = mean_absolute_error(y_test, y_pred)
ave = accuracy_score(y_test,y_pred)
r2 = r2_score(y_test, y_pred)

print(f"Mean Squared Error (MSE): {mse:.2f}")
print(f"Mean Absolute Error (MAE): {mae:.2f}")
print(f"Average precision score {ave:.2f}")
print(f"R² Score: {r2:.2f}")



#Plot the decision tree
plt.figure(figsize=(100, 40))
plot_tree(
    decision_tree=reg,
    feature_names=X_encoded.columns,
    filled=True,
    rounded=True,
    fontsize=10,
    max_depth=2,
    impurity=True,
    label='all',
    precision=0
)
plt.show()


joblib.dump(reg, 'decision_tree_regressor.joblib')

joblib.dump(X_encoded.columns.tolist(), 'encoded_columns.joblib')
