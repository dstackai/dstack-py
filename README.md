# dstack.ai

## Installation

The **dstack** package and **command line tool** must be installed with either **pip** or **Conda**:

```bash
pip install dstack
```

Note, if you use **pip**, it is highly recommended to use **virtualenv** to manage local environment. 

## Configuration

Before you can use **dstack package** in your code, you must run the **dstack command line** tool configure a **dstack profile** where you specify your [dstack.ai](https://dstack.ai) username and token.

Configuring **dstack profiles** separately from your code, allows you to make the code safe and not include plain secret tokens.

Configuring a **dstack profile** can be done by the following command:

```bash
dstack config --token <TOKEN> --user <USER>
```

In this case, the **dstack profile** name will be `default`. You can change it by including `--profile <PROFILE NAME>` in your command. This allows you to configure multiple profiles and refer to them from your code by their names.

By default, the configuration profile is stored locally, i.e. in your working directory: `<WORKING DIRECTORY>/.dstack/config.yaml`

See [CLI Reference](https://docs.dstack.ai/cli-reference) to more information about command line tools or type `dstack config --help`.

## Publishing simple plots

Once the **dstack profile** is configured, you can publish plots from your Python or R code. Let's consider two simple examples, almost identical line plots one for Python using [matplotlib](https://matplotlib.org/) library, and one for R using [ggplot2](https://ggplot2.tidyverse.org/): 

Python example:

```python
import matplotlib.pyplot as plt
from dstack import push_frame

fig = plt.figure()
plt.plot([1, 2, 3, 4], [1, 4, 9, 16])

push_frame("simple", fig, "My first plot")
library(ggplot2)
library(dstack)

df <- data.frame(x = c(1, 2, 3, 4), y = c(1, 4, 9, 16))
image <- ggplot(data = df, aes(x = x, y = y)) + geom_line()

push_frame("simple", image, "My first plot")
```

R example:

```r
library(ggplot2)
library(dstack)

df <- data.frame(x = c(1, 2, 3, 4), y = c(1, 4, 9, 16))
image <- ggplot(data = df, aes(x = x, y = y)) + geom_line()

push_frame("simple", image, "My first plot")
```

## Publishing interactive plots

In some cases, you want to have plots that are interactive and that can change when the user change its parameters. Suppose you want to publish a line plot that depends on the value of the parameter `Coefficient`.

Python example:

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
    frame.commit(line_plot(c), f"Line plot with the coefficient of {c}", {"Coefficient": c})

frame.push()
library(ggplot2)
library(dstack)
```

R example:

```r
line_plot <- function(a) {
  
    x <- c(0:20)
  
    y <- sapply(x, function(x) { return(a * x) })
  
    df <- data.frame(x = x, y = y)
  
    plot <- ggplot(data = df, aes(x = x, y = y)) + 
        geom_line() + xlim(0, 20) + ylim(0, 20)
    return(plot)

}



coeff <- c(0.5, 1.0, 1.5, 2.0)
frame <- create_frame(stack = "line_plot")

for(c in coeff) {
  
    frame <- commit(frame, line_plot(c), 
        paste0("Line plot with the coefficient of ", c), list(Coefficient = a))
}

push(frame)
```

## Documentation

For more details on the API and code samples, check out the [docs](https://docs.dstack.ai).