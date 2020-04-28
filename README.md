# dstack.ai

## Installation

The **dstack** package and **command line tool** must be installed with either **pip** or **Conda**:

```bash
pip install dstack
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
from dstack import push_frame
df = pd.read_csv(pull("my_data"))
```
As in the case of plots you can use parameters for data frames too. You can also use
data frames and plots in the same frame (with certain parameters).

## Documentation

For more details on the API and code samples, check out the [docs](https://docs.dstack.ai).
