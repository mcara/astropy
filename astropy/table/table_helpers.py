# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""
Helper functions for table development, mostly creating useful
tables for testing.
"""

import string
import warnings
from itertools import cycle

import numpy as np

from astropy.io.votable.table import parse
from astropy.utils.data import get_pkg_data_filename
from astropy.utils.data_info import ParentDtypeInfo

from .table import Column, Table


def simple_table(size=3, cols=None, kinds="ifS", masked=False):
    """
    Return a simple table for testing.

    Example
    --------
    ::

      >>> from astropy.table.table_helpers import simple_table
      >>> print(simple_table(3, 6, masked=True, kinds='ifOS'))
       a   b     c      d   e   f
      --- --- -------- --- --- ---
       -- 1.0 {'c': 2}  --   5 5.0
        2 2.0       --   e   6  --
        3  -- {'e': 4}   f  -- 7.0

    Parameters
    ----------
    size : int
        Number of table rows
    cols : int, optional
        Number of table columns. Defaults to number of kinds.
    kinds : str
        String consisting of the column dtype.kinds.  This string
        will be cycled through to generate the column dtype.
        The allowed values are 'i', 'f', 'S', 'O'.

    Returns
    -------
    out : `Table`
        New table with appropriate characteristics
    """
    if cols is None:
        cols = len(kinds)
    if cols > 26:
        raise ValueError("Max 26 columns in SimpleTable")

    columns = []
    names = [chr(ord("a") + ii) for ii in range(cols)]
    letters = np.array(list(string.ascii_letters))
    for jj, kind in zip(range(cols), cycle(kinds)):
        if kind == "i":
            data = np.arange(1, size + 1, dtype=np.int64) + jj
        elif kind == "f":
            data = np.arange(size, dtype=np.float64) + jj
        elif kind == "S":
            indices = (np.arange(size) + jj) % len(letters)
            data = letters[indices]
        elif kind == "O":
            indices = (np.arange(size) + jj) % len(letters)
            vals = letters[indices]
            data = [{val.item(): index.item()} for val, index in zip(vals, indices)]
        else:
            raise ValueError("Unknown data kind")
        columns.append(Column(data))

    table = Table(columns, names=names, masked=masked)
    if masked:
        for ii, col in enumerate(table.columns.values()):
            mask = np.array((np.arange(size) + ii) % 3, dtype=bool)
            col.mask = ~mask

    return table


def complex_table():
    """
    Return a masked table from the io.votable test set that has a wide variety
    of stressing types.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        votable = parse(
            get_pkg_data_filename("../io/votable/tests/data/regression.xml"),
            pedantic=False,
        )
    first_table = votable.get_first_table()
    table = first_table.to_table()

    return table


class ArrayWrapperInfo(ParentDtypeInfo):
    _represent_as_dict_primary_data = "data"

    def _represent_as_dict(self):
        """Represent Column as a dict that can be serialized."""
        col = self._parent
        out = {"data": col.data}
        return out

    def _construct_from_dict(self, map):
        """Construct Column from ``map``."""
        data = map.pop("data")
        out = self._parent_cls(data, **map)
        return out


class ArrayWrapper:
    """
    Minimal mixin using a simple wrapper around a numpy array.

    TODO: think about the future of this class as it is mostly for demonstration
    purposes (of the mixin protocol). Consider taking it out of core and putting
    it into a tutorial. One advantage of having this in core is that it is
    getting tested in the mixin testing though it doesn't work for multidim
    data.
    """

    info = ArrayWrapperInfo()

    def __init__(self, data, copy=True):
        if isinstance(data, ArrayWrapper):
            # this is done to preserve byteorder through copies
            arr = data.data
        else:
            arr = data
        self.data = np.array(arr, copy=copy)
        if "info" in getattr(data, "__dict__", ()):
            self.info = data.info

    def __getitem__(self, item):
        if isinstance(item, (int, np.integer)):
            out = self.data[item]
        else:
            out = self.__class__(self.data[item], copy=False)
            if "info" in self.__dict__:
                out.info = self.info
        return out

    def __setitem__(self, item, value):
        self.data[item] = value

    def __len__(self):
        return len(self.data)

    def __eq__(self, other):
        """Minimal equality testing, mostly for mixin unit tests."""
        if isinstance(other, ArrayWrapper):
            return self.data == other.data
        else:
            return self.data == other

    @property
    def dtype(self):
        return self.data.dtype

    @property
    def shape(self):
        return self.data.shape

    def __repr__(self):
        return f"<{self.__class__.__name__} name='{self.info.name}' data={self.data}>"
