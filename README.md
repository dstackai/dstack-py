# dstack.ai

## Installation

The **dstack** package and **command line tool** must be installed with either **pip** or **Conda**:

```bash
pip install dstack
```
or
```bash
conda install -c dstack.ai dstack
```
Note, *only* Python 3 is supported and if you use **pip**, it is highly recommended to use **virtualenv** to manage local environment. 

## Configuration

Before you can use **dstack package** in your code, you must run the **dstack command line** tool configure a **dstack profile** where you specify your [dstack.ai](https://dstack.ai) username and token.

Configuring **dstack profiles** separately from your code, allows you to make the code safe and not include plain secret tokens.

Configuring a **dstack profile** can be done by the following command:

```bash
dstack config add --token <TOKEN> --user <USER>
```
or simply
```bash
dstack config add
```
In this case, the **dstack profile** name will be `default`. You can change it by using extended syntax of the command:
 ```bash
dstack config add <PROFILE_NAME>
```

This allows you to configure multiple profiles and refer to them from your code by their names.

By default, the configuration profile is stored in your home directory: `$HOME/.dstack/config.yaml`.

---

**NOTE**

Before version 0.4.2 config was stored in a working directory. Please, do not forget to move the
local config into your home directory.

---

If you use proxy it would be useful to disable SSL certificate check. To do that use `--no-verify` option for selected profile in command line.

See [CLI Reference](https://docs.dstack.ai/cli-reference) to more information about command line tools or type `dstack config --help`.

## How to install dstack server locally
From version 0.4 it is possible to use a local version of [dstack](https://github.com/dstackai/dstack) 
server.
 
To start it, use the following command:
```bash
dstack server start
```
This command installs the latest version (if it's not installed) of the server and starts it. If environment variable `JAVA_HOME` is set
and version of JDK is compatible with the server, that version will be used. In the case if 
installer can't find `JAVA_HOME` or JDK version is incompatible with current server version
it will download a compatible version by itself. To update server use `dstack server update`. 

Follow instructions provided by the server in the terminal.

Use `dstack server --help` for more information.

## Publishing simple plots

Once the **dstack profile** is configured, you can publish plots from your Python program or Jupyter notebook. Let's consider the simpliest example, line plot using [matplotlib](https://matplotlib.org/) library, but you can use [bokeh](https://docs.bokeh.org/en/latest/index.html) and [plotly](https://plot.ly) plots instead of matplotlib in the same way: 
```python
import matplotlib.pyplot as plt
import dstack as ds

fig = plt.figure()
plt.plot([1, 2, 3, 4], [1, 4, 9, 16])

ds.push("simple", fig, "My first plot")
```

## Publishing interactive plots

In some cases, you want to have plots that are interactive and that can change when the user change its parameters. Suppose you want to publish a line plot that depends on the value of the parameter `Coefficient` (slope).
```python
import matplotlib.pyplot as plt
import dstack as ds

def line_plot(a):
    xs = range(0, 21)
    ys = [a * x for x in xs]
    fig = plt.figure()
    plt.axis([0, 20, 0, 20])
    plt.plot(xs, ys)
    return fig


frame = ds.frame("line_plot")
coeff = [0.5, 1.0, 1.5, 2.0]

for c in coeff:
    frame.add(line_plot(c), f"Line plot with the coefficient of {c}", Coefficient=c)

frame.push()
```
In case when parameter's name contains space characters, `params` dictionary argument must be used, e.g.:
```python
frame.add(my_plot, "My plot description", params={"My parameter": 0.02})
```  
Of course, you can combine two approaches together, it can be especially useful in case of 
comprehensive frames with multiple parameters. In this case parameters which are passed by named arguments
will be merged to `params` dictionary. So, the following line
```python
frame.add(my_plot, "My plot description", params={"My parameter": 0.02}, other=True)
```
produces the same result as this one:
```python
frame.add(my_plot, "My plot description", params={"My parameter": 0.02, "other": True})
```
You can use `push` with message to add information related 
to this particular revision: `push("Fix log scale")`. Function `push_frame` can accept message as well.

## Working with datasets
The **dstack**  package can be used not only publishing plots from popular visualizations packages,
bit to publish [pandas](https://pandas.pydata.org/) data frame as well. How you can do it?
It can be done in the same way as in the case of plots by replacing plot to pandas data frame object.
Here is an example:
```python
import pandas as pd
import dstack as ds

raw_data = {"first_name": ["John", "Donald", "Maryam", "Don", "Andrey"], 
        "last_name": ["Milnor", "Knuth", "Mirzakhani", "Zagier", "Okunkov"], 
        "birth_year": [1931, 1938, 1977, 1951, 1969], 
        "school": ["Princeton", "Stanford", "Stanford", "MPIM", "Princeton"]}

df = pd.DataFrame(raw_data, columns = ["first_name", "last_name", "birth_year", "school"])

ds.push("my_data", df, "DataFrame example")
```
In some cases you not only want to store dataset but retrieve it. You can `pull` data frame
object from the stack:
```python
import dstack as ds
df = ds.pull("my_data")
```
As in the case of plots you can use parameters for data frames too. You can also use
data frames and plots in the same frame (with certain parameters). It will work with
`Series` as well.

## GeoPandas support
You can also push and pull GeoDataFrame from [GeoPandas](https://geopandas.org/):
```python
import geopandas
import pandas as pd

import dstack as ds

df = pd.DataFrame({'City': ['Buenos Aires', 'Brasilia', 'Santiago', 'Bogota', 'Caracas'],
                   'Country': ['Argentina', 'Brazil', 'Chile', 'Colombia', 'Venezuela'],
                   'Latitude': [-34.58, -15.78, -33.45, 4.60, 10.48],
                   'Longitude': [-58.66, -47.91, -70.66, -74.08, -66.86]})

gdf = geopandas.GeoDataFrame(
    df, geometry=geopandas.points_from_xy(df.Longitude, df.Latitude))

ds.push("my_first_geo", gdf)
```
To pull the GeoDataFrame object just call `my_gdf = ds.pull("my_first_geo")`.

## Pushing and pulling ML models
It is also possible to store ML models using `push` and `pull`. Right now such popular
ML frameworks and libraries like [PyTorch](https://pytorch.org/), [TensorFlow](https://www.tensorflow.org/) and 
[scikit-learn](https://scikit-learn.org) are supported.

Suppose you have a PyTorch model, for example linear one:
```python
import torch
import dstack as ds
from dstack.torch.handlers import TorchModelEncoder

# define a new model
class LinearRegression(torch.nn.Module):
    def __init__(self, input_size, output_size):
        super(LinearRegression, self).__init__()
        self.linear = torch.nn.Linear(input_size, output_size)

    def forward(self, x):
        out = self.linear(x)
        return out

model = LinearRegression(1, 1)

# here you are training the model
for epoch in range(100):
    ...

# to avoid compatibility issues we will store only model weights   
TorchModelEncoder.STORE_WHOLE_MODEL = False

# and finally push the model
ds.push("my_torch_model", model, "My first PyTorch model")        
```  
We stored only model weights, so to pull it we should provide model
class to decoder, because `pull` method is not smart enough to guess which
particular class to use. The following example shows a common pattern how to use
pull in this case:
```python
import dstack as ds
from dstack.torch.handlers import TorchModelWeightsDecoder

my_model = ds.pull("my_torch_model", decoder=TorchModelWeightsDecoder(LinearRegression(1, 1)))
```

In the case of TensorFlow (only version 2 is supported), let's use predefined models to
show how to deal with them (for custom models technique will be the same as in the case
of PyTorch which is described above).

```python
import dstack as ds
import tensorflow as tf

d = 30

model = tf.keras.models.Sequential([
    tf.keras.layers.Input(shape=(d,)),
    tf.keras.layers.Dense(1, activation="sigmoid")
])

# train the model here

# push the model
ds.push("my_tf_model", model, "My first TF model")
```
To pull model you need simply call `pull`, because the model is standard no additional
information required:
```python
import dstack as ds

model1 = ds.pull("my_tf_model")
```

In the case of scikit-learn all thing as simple as in the TensorFlow case:
```python
import dstack as ds
from sklearn.linear_model import LinearRegression

# train the simple Linear regression
model = LinearRegression()

# train the model as usual

# push it
ds.push("my_linear_model", model, "My first linear model")
```
To pull the model in this case call `pull("my_linear_model")`.

## Documentation

For more details on the API and code samples, check out the [docs](https://docs.dstack.ai).
