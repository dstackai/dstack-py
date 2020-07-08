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
dstack config --token <TOKEN> --user <USER>
```
or simply
```bash
dstack config
```
In this case, the **dstack profile** name will be `default`. You can change it by including `--profile <PROFILE NAME>` in your command. This allows you to configure multiple profiles and refer to them from your code by their names.

By default, the configuration profile is stored locally, i.e. in your working directory: `<WORKING_DIRECTORY>/.dstack/config.yaml`

If you use proxy it would be useful to disable SSL certificate check. To do that use `--no-verify` option for selected profile in command line.

See [CLI Reference](https://docs.dstack.ai/cli-reference) to more information about command line tools or type `dstack config --help`.

## How to install dstack server locally
From version 0.4 it is possible to use a local version of [dstack](https://github.com/dstackai/dstack) 
server.
 
To install it, use the following command:
```bash
dstack server --install
```
This command installs the latest version of the server. If environment variable `JAVA_HOME` is set
and version of JDK is compatible with the server, that version will be used. In the case if 
installer can't find `JAVA_HOME` or JDK version is incompatible with current server version
it will download a compatible version by itself. To update server use `dstack server --update`. 

After install/update the server can be started by `dstack server --start` (if you try to 
run this command before `--install`, server will be installed automatically). 
Follow instructions provided by the server in the terminal.

Use `dstack server --help` for more information.

## Publishing simple plots

Once the **dstack profile** is configured, you can publish plots from your Python program or Jupyter notebook. Let's consider the simpliest example, line plot using [matplotlib](https://matplotlib.org/) library, but you can use [bokeh](https://docs.bokeh.org/en/latest/index.html) and [plotly](https://plot.ly) plots instead of matplotlib in the same way: 
```python
import matplotlib.pyplot as plt
from dstack import push_frame

fig = plt.figure()
plt.plot([1, 2, 3, 4], [1, 4, 9, 16])

push_frame("simple", fig, "My first plot")
```

## Publishing interactive plots

In some cases, you want to have plots that are interactive and that can change when the user change its parameters. Suppose you want to publish a line plot that depends on the value of the parameter `Coefficient` (slope).
```python
import matplotlib.pyplot as plt
from dstack import create_frame

def line_plot(a):
    xs = range(0, 21)
    ys = [a * x for x in xs]
    fig = plt.figure()
    plt.axis([0, 20, 0, 20])
    plt.plot(xs, ys)
    return fig


frame = create_frame("line_plot")
coeff = [0.5, 1.0, 1.5, 2.0]

for c in coeff:
    frame.commit(line_plot(c), f"Line plot with the coefficient of {c}", Coefficient=c)

frame.push()
```
In case when parameter's name contains space characters, `params` dictionary argument must be used, e.g.:
```python
frame.commit(my_plot, "My plot description", params={"My parameter": 0.02})
```  
Of course, you can combine two approaches together, it can be especially useful in case of 
comprehensive frames with multiple parameters. In this case parameters which are passed by named arguments
will be merged to `params` dictionary. So, the following line
```python
frame.commit(my_plot, "My plot description", params={"My parameter": 0.02}, other=True)
```
produces the same result as this one:
```python
frame.commit(my_plot, "My plot description", params={"My parameter": 0.02, "other": True})
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
from dstack import push_frame
raw_data = {"first_name": ["John", "Donald", "Maryam", "Don", "Andrey"], 
        "last_name": ["Milnor", "Knuth", "Mirzakhani", "Zagier", "Okunkov"], 
        "birth_year": [1931, 1938, 1977, 1951, 1969], 
        "school": ["Princeton", "Stanford", "Stanford", "MPIM", "Princeton"]}
df = pd.DataFrame(raw_data, columns = ["first_name", "last_name", "birth_year", "school"])
push_frame("my_data", df, "DataFrame example")
```
In some cases you not only want to store dataset but retrieve it. You can `pull` data frame
object from the stack:
```python
import pandas as pd
from dstack import pull
df = pull("my_data")
```
As in the case of plots you can use parameters for data frames too. You can also use
data frames and plots in the same frame (with certain parameters). It will work with
`Series` as well.

## Pushing and pulling ML models
It is also possible to store ML models using `push` and `pull`. Right now such popular
ML frameworks and libraries like [PyTorch](https://pytorch.org/), [TensorFlow](https://www.tensorflow.org/) and 
[scikit-learn](https://scikit-learn.org) are supported.

Suppose you have a PyTorch model, for example linear one:
```python
import torch
from dstack import push_frame
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
push_frame("my_torch_model", model, "My first PyTorch model")        
```  
We stored only model weights, so to pull it we should provide model
class to decoder, because `pull` method is not smart enough to guess which
particular class to use. The following example shows a common pattern how to use
pull in this case:
```python
from dstack.torch.handlers import TorchModelWeightsDecoder
from dstack import pull

my_model = pull("my_torch_model", decoder=TorchModelWeightsDecoder(LinearRegression(1, 1)))
```

In the case of TensorFlow (only version 2 is supported), let's use predefined models to
show how to deal with them (for custom models technique will be the same as in the case
of PyTorch which is described above).

```python
from dstack import push_frame
import tensorflow as tf

d = 30

model = tf.keras.models.Sequential([
    tf.keras.layers.Input(shape=(d,)),
    tf.keras.layers.Dense(1, activation="sigmoid")
])

# train the model here

# push the model
push_frame("my_tf_model", model, "My first TF model")
```
To pull model you need simply call `pull`, because the model is standard no additional
information required:
```python
from dstack import pull

model1 = pull("my_tf_model")
```

In the case of scikit-learn all thing as simple as in the TensorFlow case:
```python
from sklearn.linear_model import LinearRegression
from dstack import push_frame

# train the simple Linear regression
model = LinearRegression()

# train the model as usual

# push it
push_frame("my_linear_model", model, "My first linear model")
```
To pull the model in this case call `pull("my_linear_model")`.

## Documentation

For more details on the API and code samples, check out the [docs](https://docs.dstack.ai).
