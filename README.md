# qatools
Quality Assesment Tools for ALMA Observatory

Includes tools for manipulating ALMA raw data, implementing methods to access the specifications on this document: http://almasw.hq.eso.org/almasw/pub/HLA/ASDMImplementation2FBT/SDMTables_postSDM2FBT.pdf

It provides methods like:

def getTable(self, rownum = None):
  """Returns the content of a particular table in a python list"""

def getXPath(self):

def getFields(self):
  """Returns a python list containing all field names for this ASDMTable object"""

def getValue(self, fieldname, rownum = None):
  """
  Returns the value of a specific field for this ASDM object
  If rownum is not specified, returns all values
  """
