import matplotlib.pyplot as plt
import numpy as np
from dstack.stack import create_frame
from dstack.matplotlib import MatplotlibHandler

if __name__ == "__main__":
    frame = create_frame(stack="cheptsov/test",
                         token="f71e42ae-5209-4d21-933c-883d75722cf6",
                         handler=MatplotlibHandler())

    t = np.arange(0.0, 2.0, 0.01)
    s = 1 + np.sin(2 * np.pi * t)

    fig, ax = plt.subplots()
    ax.plot(t, s)

    ax.set(xlabel='t', ylabel='x',
           title='Very simple plot')
    ax.grid()

    frame.commit(fig, 'Very simple plot')
    frame.push()
