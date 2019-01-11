# -*- coding: utf-8 -*-

# Section: Classes definitions
class ASDMTable:
	def __init__(self, name, uid):
		self.name = name
		self.uid = uid
		if name[-5:] != "Table": name += 'Table'
		self.allfields = tuple([i[0] for i in getColumnDefs(name)])
		self.xmltext, self.timestamp = xmlTableExport(name, uid)
		self.is_bin = False
		if self.xmltext == '':
			self.xdict = dict()
			self.asdm_uid = ''
		else:
			self.xdict = xml2xdict(xmlstring = self.xmltext)
			self.asdm_uid = self.xdict [(name, 1)][0][('ContainerEntity', 1)][2]['entityId']
			if ('Attributes', 1) in self.xdict[(name, 1)][0] and ('BulkStoreRef', 1) in self.xdict[(name, 1)][0]:
				self.is_bin = True

	def getTable(self, rownum = None):
		"""Returns the content of a particular table in a python list"""
		from os import environ
		if self.is_bin:
			from subprocess import getoutput
			#cmd  = environ['AIDA_BASE'] + '/util/'
			cmd  = 'source /users/fmorales/opt/aida/etc/aidaenv.sh ; '
			cmd += '/users/fmorales/opt/aida/util/'
			cmd += "get" + self.name + ".py --dir=" + getTableBin(self.asdm_uid, self.uid, self.name)
			out = getoutput(cmd)
			exec(out)
			return(locals()['table'])
		else:
			if rownum == None:
				return(xdict2table(self.xdict))
			else:
				return(xdict2row(self.xdict, rownum))

	def getXPath(self):
		return(dict(xdict2list(self.xdict)))

	def getFields(self):
		"""Returns a python list containing all field names for this ASDMTable object"""
		return(xdict2fields(self.xdict))

	def getValue(self, fieldname, rownum = None):
		"""
		Returns the value of a specific field for this ASDM object
		If rownum is not specified, returns all values
		"""
		if rownum == None:
			return(xdict2value(self.xdict, fieldname, None)) 
		else:
			return(xdict2value(self.xdict, fieldname, rownum)) 

class ASDMIndex:
	def __init__(self, uid):
		self.name = 'ASDM'
		self.allfields = [('tablename', 'text'), ('numberrows', 'number'), ('asdmtable_uid', 'text')]
		self.uid = uid
		self.xmltext, self.timestamp = xmlTableExport(self.name, uid)
		if self.xmltext != '':
			self.xdict = xml2xdict(xmlstring = self.xmltext)
			self.timeofcreation = self.xdict[('ASDM', 1)][0][('TimeOfCreation', 1)][1]
		else:
			self.xdict = ''
			self.timeofcreation = ''

	def getTable(self):
		"""Returns the content of ASDM.xml in a python list"""
		d = self.getDict()
		table = [(i, d[i][0], d[i][1]) for i in d]
		table.sort()
		return(table)

	def getFields(self):
		return(self.allfields)

	def getDict(self):
		"""Returns the content of ASDM.xml in a simple dictionary[tablename] = (numberrows, asdmtable_uid)"""	
		asdmIndexDict = dict()
		n = 1
		while True:
			if ("Table", n) in self.xdict[("ASDM", 1)][0]:
				table_name = self.xdict[("ASDM", 1)][0][("Table", n)][0][("Name", 1)][1]
				numberrows = self.xdict[("ASDM", 1)][0][("Table", n)][0][("NumberRows", 1)][1]
				if numberrows != "0":
					asdmtable_uid = self.xdict[("ASDM", 1)][0][("Table", n)][0][("Entity", 1)][2]["entityId"]
				else:
					asdmtable_uid = ""
				asdmIndexDict[table_name] = (numberrows, asdmtable_uid)
			else:
				break
			n += 1
		return(asdmIndexDict)

class APDMTable():
	def __init__(self, name, uid):
		self.name = name
		self.uid = uid		
		self.xmltext, self.timestamp = xmlTableExport(name, uid)
		if self.xmltext == '':
			self.xdict = dict()
		else:
			self.xdict = xml2xdict(xmlstring = self.xmltext)

	def getXPath(self):
		return(dict(xdict2list(self.xdict)))

class aidaTable:
	def __init__(self, name = '', statement = '', fields = []):
		self.name = name
		self.statement = statement
		self.fields = fields
		self.row = dict()
		self.title = ''
		self.data = list()

	def append(self, row=dict()):
		if row == dict():
			row = self.row
		self.data.append(tuple([row[k[0]] for k in self.fields]))

	def fromASDMIndex(self, asdmindex):
		self.fields = asdmindex.allfields
		self.data = asdmindex.getTable()
		self.name = asdmindex.name

	def fromASDMTable(self, asdmtable):
		self.fields = [('row',)]
		for i in asdmtable.allfields:
			self.fields.append((i,))
		self.data = asdmtable.getTable()
		self.name = asdmtable.name

	def fromArchive(self, sqltxt = ''):
		global conn_metadata
		cursor = conn_metadata.cursor()
		cursor.execute(sqltxt)
		self.statement = sqltxt
		self.fields = list()
		for i in cursor.description:
			self.fields.append((i[0], i[1]))
		self.data = cursor.fetchall()

	def fromRamDb(self, sqltxt = ''):
		global ramdb_conn
		cursor = ramdb_conn.cursor()
		cursor.execute(sqltxt)
		self.statement = sqltxt
		self.fields = list()
		for i in cursor.description:
			self.fields.append((i[0],)) # TODO: check datatypes from sqlite
		self.data = cursor.fetchall()

	def fromAidaDb(self, sqltxt = ''):
		global conn_aidadb
		cursor = conn_aidadb.cursor()
		cursor.execute(sqltxt)
		self.statement = sqltxt
		self.fields = list()
		for i in cursor.description:
			self.fields.append((i[0],)) # TODO: check datatypes from postgres
		self.data = cursor.fetchall()

	def toRamDb(self, drop=False):
		global ramdb_conn
		ramdb_cursor = ramdb_conn.cursor()
	
		qmark = ""

		ddl = 'create table if not exists ' + self.name + '(\n'
		for f in self.fields:
			if len(f) == 1:
				f = (f[0], 'str')
			ddl += '  ' + f[0] + ' ' +  typemap(f[1]) + ",\n"
			qmark += "?, "
		
		ddl = ddl[:-2]
		ddl += '\n)'

		ramdb_cursor.execute(ddl)
		
		if drop:
			sql = "delete from " + self.name +" where 1 = 1"
			ramdb_cursor.execute(sql)
		ramdb_cursor.executemany("insert into " + self.name + " values (" + qmark[:-2] + ")", self.data)
		ramdb_cursor.close()

	def toAidaDb(self, drop=False):
		global conn_aidadb
		cursor = conn_aidadb.cursor()
	
		fields = ""
		qmark = ""

		ddl = 'create table if not exists ' + self.name + '(\n'
		for f in self.fields:
			if len(f) == 1:
				f = (f[0], 'str')
			ddl += '  ' + f[0] + ' ' +  typemap(f[1]) + ",\n"
			qmark += "%s, "
		
		ddl = ddl[:-2]
		ddl += '\n)'
		cursor.execute(ddl)

		if drop:
			sql = "delete from " + self.name +" where 1 = 1"
			cursor.execute(sql)

		sql = "insert into " + self.name + " values (" + qmark[:-2] + ")"
		cursor.executemany(sql, self.data)
		conn_aidadb.commit()
		cursor.close()

	def getCSV(self, separator = ',', fixed=False):
		"""Returns a string containing header and data of an aidaTable object."""

		# Get the max width for each field
		width = dict()
		for i in range(0, len(self.fields)):
			width[i] = 0
	
		if fixed:	
			for i in self.data + [[f[0] for f in self.fields]]:
				x = 0
				for j in i:
					if len(str(j)) > width[x]:
						width[x] = len(str(j))
					x = x + 1
		##
		csv = ''
		x = 0
		for h in self.fields:
			csv += h[0].ljust(width[x]) + separator
			x += 1
		csv = csv[:-(len(separator))] + '\n'

		for d in sorted(self.data):
			x = 0
			for c in d:
				csv += str(c).ljust(width[x]) + separator
				x += 1
			csv = csv[:-(len(separator))] + '\n'
		return(csv[:-1])

def ramDb(table):
	global ramdb_conn
	ramdb_cursor = ramdb_conn.cursor()

	fields = ""
	qmark = ""
	for f in table.fields:
		fields += f[0] + " text, "
		qmark += "?, "
	ramdb_cursor.execute("create table " + table.name + " (" + fields[:-2] + ")")
	ramdb_cursor.executemany("insert into " + table.name + " values (" + qmark[:-2] + ")", table.data)
	ramdb_cursor.close()

# Section: Miscelaneous FXs
def uid2fsuid(uid):
	"""Returns a uid in filesystem format."""
	return(uid.replace("/", "_").replace(":", "_"))

def normalize_uid(uid):
	nuid = uid.replace("uid", "")
	nuid = nuid.replace("/", "_")
	nuid = nuid.replace(":", "")
	nuid = nuid.replace("_A", "A")
	nuid = nuid.replace("_A", "A")
	nuid = nuid.replace("_A", "A")
	return(nuid)

def adict2list(adict):
	alist = list()
	for a in adict:
		alist.append([a, adict[a]])
	return(alist)

def getchilds(node):
	ydict = dict()
	for child in node:
		tag = child.tag.rsplit("}")[-1]
		if (tag, 1) in ydict:
			i = 1
			for k in ydict:
				if k[0] == tag:
					if k[1] > i:
						i = k[1]
			i = i + 1
		else:
			i = 1
		if child.text == None:
			txt = ""
		else:
			txt = (child.text).strip()
		ydict[(tag, i)] = [getchilds(child), txt, child.attrib]
	return(ydict)

def xdict2list(xdict = {}, xpath = ""):
	xlist = []
	for i in xdict:
		xp = xpath + "/" + i[0] + "[" + str(i[1]) + "]"
		xlist.append([xp, (xdict[i])[1]])
		for l in adict2list((xdict[i])[2]):
			xlist.append([xp + "/@" + l[0], l[1]])
		xlist = xlist + xdict2list((xdict[i])[0], xp)
	return(xlist)

def xml2xdict(xmlstring = '', filename = ''):
	"""Returns a xdict (a recursive python dictionary containing an xml document)"""
	from xml.etree.ElementTree import parse, XML 
	# Parse root node and extract text and attributes
	if filename == '':
		if xmlstring == '':
			return(dict())
		else:
			try:
				root = (XML(xmlstring))
			except:
				print(xmlstring)
	else:
		root = (parse(filename)).getroot()
		
	xdict = dict()
	tag = root.tag.rsplit("}")[-1]
	 
	if root.text == None:
		txt = ""
	else:
		txt = (root.text).strip()
	xdict[(tag, 1)] = [getchilds(root), txt, root.attrib]

	del(root)
	return(xdict)

def detect_convert_from_string(string):
	from ast import literal_eval
	try:
		t = type(literal_eval(string))
		if t is int:
			return(t, int(string))
		elif t is float:
			return(t, float(string))
		else:
			return(t, string)
	except:
		return(type(""), string)

def dim_asdm_array(string):
	alist = string.split()
	lenlist = len(alist)
	if lenlist < 2:
		return(0)
	else:
		try:
			d = int(alist[0])
		except:
			return(0)
		if d == 1:
			try:
				i = int(alist[1])
			except:
				return(0)
			if i + 2  != lenlist:
				return(0)
		elif d == 2:
			try:
				i, j = int(alist[1]), int(alist[2])
			except:
				return(0)
			if i * j + 3 != lenlist:
				return(0)
		elif d == 3:
			try:
				i, j, k = int(alist[1]), int(alist[2]), int(alist[3])
			except:
				return(0)
			if i * j * k + 4 != lenlist:
				return(0)
		elif d > 3:
			return(0)
		return(d)

def array2list(dim, thisarr):
	array = list()
	thisarr = thisarr.strip().split()
	if dim == 1:
		dimensions = [int(thisarr[1]), 0, 0]
		arr = thisarr[2:]
		rk = 1
		rj = 0
		ri = 0
	elif dim == 2:
		dimensions = [int(thisarr[2]), int(thisarr[1]), 0]
		arr = thisarr[3:]
		rk = 1
		rj = 1
		ri = 0
	else:
		dimensions = [int(thisarr[3]), int(thisarr[2]), int(thisarr[1])]
		arr = thisarr[4:]
		rk = 1
		rj = 1
		ri = 1
	n = 0
	for k in range(rk, dimensions[0] + 1):
		for j in range(rj, dimensions[1] + 1):
			for i in range(ri, dimensions[2] + 1):
				array.append([k, j, i, arr[n]])
				n = n + 1
	return(array)

def vector2csv(vector):
	string = ""
	for v in vector:
		string += str(v) + "|'|"
	string = string [:-3] + "\n"
	return(string) 
	
def xmltable2csv(xml_filename, timestamp = "2000-01-01 00:00:00.000", fields_filename = "/tmp/fields_filename.csv", arrays_filename = "/tmp/arrays_filename.csv"):
	from os import remove, system

	# xdict is a dictionary containing the whole xml document
	xdict = xml2xdict(xml_filename)
	for tablename in xdict:
		break
	
	# Extracting table identification
	tablename = tablename[0]
	asdm_uid  = xdict[(tablename, 1)][0][('ContainerEntity', 1)][2]['entityId']
	asdmtable_uid = xdict[(tablename, 1)][0][('Entity', 1)][2]['entityId']
	
	# columns is a dict containing tablenames as the key, and the position as the value {'temperature': 1, 'sizeerr': 2 , ...}
	columns = dict()
	empty = list()
	n = 0
	for c in get_asdm_columns():
		if c[1] == tablename[:-5].lower() and c[4] == 0:
			columns[c[2]] = n
			n = n + 1
			empty.append("")

	# The field names as the header of csv file	
	header = list(empty)
	for c in columns:
		header[columns[c]] = c
	
	# Open the csv files and write the headers
	of_fields = open(fields_filename, "w")
	of_arrays = open(arrays_filename, "w")
	of_fields.write(vector2csv(["asdmtable_uid", "rown", "asdm_uid" , "timestamp"] + header))
	#of_arrays.write(vector2csv(["tablename", "asdmtable_uid", "rown" , "i", "j", "k", "data"]))

	empty_file_fields_flag = True
	arraytables = set()
	empty_file_arrays_flag = True
	# Procedure to extract rows from xml
	for row in xdict[(tablename, 1)][0]:
		if row[0] == 'row':
			rownum = row[1]
			rowdict = xdict[(tablename, 1)][0][row][0]
			thisrow = list(empty)
			# Procedure to extract columns
			for column in rowdict:
				if rowdict[column][0] != {}:
					data = rowdict[column][0][('EntityRef', 1)][2]['entityId']
				else:
					data = rowdict[column][1].strip()
				if detect_convert_from_string(data)[0] is str:
					dim = dim_asdm_array(data)
					if dim > 0:
						# We have an array here of dimension dim
						for i in asdm_array2list(dim, data):
							empty_file_arrays_flag = False
							of_arrays.write(vector2csv(([(tablename.replace("Table", "")[:5] + "_" + column[0][:20]).lower(), asdmtable_uid, rownum] + i)))
							arraytables.add((tablename.replace("Table", "")[:5] + "_" + column[0][:20]).lower())
					else:
						# We have a simple string here
						thisrow[columns[column[0].lower()]] = data
				else:
					# We have a number here
					thisrow[columns[column[0].lower()]] = data
			empty_file_fields_flag = False
			of_fields.write(vector2csv([asdmtable_uid, rownum, asdm_uid, timestamp] + thisrow))

	of_arrays.close()
	of_fields.close()
	
	# Split csv arrays file 
	for a in arraytables:
		system("grep \"" + a + "|'|\" " + arrays_filename +" > " + arrays_filename[:-3] + a + ".csv")

	# Remove unuseful csv empty files
	try:
		if empty_file_fields_flag:
			remove(fields_filename)
		if empty_file_arrays_flag:
			remove(arrays_filename)
	except:
		print("Warning: some files could not be deleted.")

	# Split array csv files

	del(xdict)

def asdmxml2csv(xml_filename, timestamp = "2000-01-01 00:00:00.000", asdm_filename = "/tmp/ASDM.xml.csv", asdmtable_filename = "/tmp/ASDM.xml.asdmtable.csv"):

	xdict = xml2xdict(xml_filename)
	time_of_creation = xdict[("ASDM", 1)][0][("TimeOfCreation", 1)][1]
	asdm_uid = xdict[("ASDM", 1)][0][("Entity", 1)][2]["entityId"]

	# Write ASDM.xml.csv file
	of_asdm = open(asdm_filename, "w")
	of_asdm.write(vector2csv(["asdm_uid", "timestamp", "timeofcreation"]))
	of_asdm.write(vector2csv([asdm_uid, timestamp, time_of_creation]))
	of_asdm.close()

	# Write ASDM.xml.asdmtable.csv file
	of_asdmtable = open(asdmtable_filename, "w")
	of_asdmtable.write(vector2csv(["asdmtable_uid", "asdm_uid", "tablename", "numberrows"]))
	for i in range(1, 64):
		if ("Table", i) in xdict[("ASDM", 1)][0]: # some asdms have 62 tables instead of 63
			table_name = xdict[("ASDM", 1)][0][("Table", i)][0][("Name", 1)][1]
			numberrows = xdict[("ASDM", 1)][0][("Table", i)][0][("NumberRows", 1)][1]
			if numberrows != "0": # do not store empty tables references
				asdmtable_uid = xdict[("ASDM", 1)][0][("Table", i)][0][("Entity", 1)][2]["entityId"]
				of_asdmtable.write(vector2csv([asdmtable_uid, asdm_uid, table_name, numberrows]))
	of_asdmtable.close()


def sdmTimeString(t, length = "l"):
	"""
	Convert a time value (as used by ASDM, i.e. MJD in nanoseconds) into a FITS type string.
	"""
	from time import strftime, gmtime
	st = t / 1000000000
	# decimal microseconds ...
	t = (t - st * 1000000000) / 1000
	# number of seconds since 1970-01-01T00:00:00
	st = st - 3506716800
	if length == 'l':
		return strftime("%Y/%m/%d/%H:%M:%S", gmtime(st)) + (".%2.2d" % t)
	else:
		return strftime("%H:%M:%S", gmtime(st)) + (".%2.2d" % t)

# Section: Core FXs

def xmlTableExport(tablename, uid):
	"""For a given table name and uid, returns the xml text and timestamp."""
	global conn_metadata
	global oratables_map
	if tablename in oratables_map:
		# Section: Extract ASDM.xml file
		sql  = "select xmltype.getclobval(xml), timestamp from alma." + oratables_map[tablename] + " where archive_uid='" + uid + "'"
		cursor = conn_metadata.cursor()
		cursor.execute(sql)

		xmldoc = cursor.fetchone()
		if xmldoc == None:
			#print("ERROR: UID not found. Exiting.")
			return(('', ''))
	else:
		print("ERROR: Wrong table name")
		return(('', ''))

	return((xmldoc[0].read(), xmldoc[1]))

def getTableBin(asdm_uid, asdmtable_uid, tablename, tmpdir = "/tmp"):
	from urllib.request import urlretrieve
	from os import mkdir
	from random import choice

	global ngassrv

	if len(tmpdir) > 0:
		if tmpdir[-1] == "/":
			tmpdir = tmpdir[:-1]
	else:
		tmpdir = "."

	try:
		asdmdir = asdm_uid.replace(':','_')
		asdmdir = asdmdir.replace('/','_')
		asdmdir = tmpdir + "/" + asdmdir
		mkdir(asdmdir)
	except:
		print("WARNING: Same UID in current directory. Overwriting.")

	xmltext, timestamp = xmlTableExport('ASDM', asdm_uid)
	of = open(asdmdir + "/ASDM.xml", "w")
	of.write(xmltext)
	of.close()
	
	urlretrieve("http://" + choice(ngassrv) + "/RETRIEVE?file_id=" + asdmtable_uid[6:], filename = asdmdir + "/" + tablename.replace('Table','') + '.bin')

	return(asdmdir)	

def getColumnDefs(tablename):
	global asdm_datamodel
	col_defs = []
	for c in asdm_datamodel:
		if c[1] == tablename:
			col_defs.append(c[2:])
	return(col_defs)

def xdict2table(xdict):
	tablename = tuple(xdict.keys())[0][0]
	col_defs = getColumnDefs(tablename)
	table = []
	n = 1
	while True:
		if ('row', n) in xdict[(tablename, 1)][0]:
			row = xdict[(tablename, 1)][0][('row', n)]
			newrow = [n]
			for c in col_defs:
				if (c[0], 1) in row[0]:
					if c[1] == 'EntityRef':
						newrow.append(row[0][(c[0], 1)][0]['EntityRef', 1][2]['entityId'])
					else:
						newrow.append(row[0][(c[0], 1)][1])
				else:
					newrow.append(None)
				pass
		else:
			break
		n = n + 1
		table.append(tuple(newrow))
	return(table)

def xdict2row(xdict, rownum):
	tablename = tuple(xdict.keys())[0][0]
	col_defs = getColumnDefs(tablename)
	if ('row', rownum) in xdict[(tablename, 1)][0]:
		row = xdict[(tablename, 1)][0][('row', rownum)]
		newrow = [rownum]
		for c in col_defs:
			if (c[0], 1) in row[0]:
				if c[1] == 'EntityRef':
					newrow.append(row[0][(c[0], 1)][0]['EntityRef', 1][2]['entityId'])
				else:
					newrow.append(row[0][(c[0], 1)][1])
			else:
				newrow.append(None)
			pass
	else:
		return([tuple()])
	return([tuple(newrow)])

def xdict2value(xdict, fieldname, rown = None):
	tablename = tuple(xdict.keys())[0][0]
	col_defs = getColumnDefs(tablename)
	col_defs = dict([(row[0], row[1:]) for row in col_defs]) # Transform a multidimensional list in a dictionary with first column as key

	if rown == None:
		rownum = 1
	else:
		rownum = rown
 
	newrow = []
	while True:
		if ('row', rownum) in xdict[(tablename, 1)][0]:
			if (fieldname, 1) in xdict[(tablename, 1)][0][('row', rownum)][0]:
				field = xdict[(tablename, 1)][0][('row', rownum)][0][(fieldname, 1)]
				arraydimension = int(col_defs[fieldname][1])
				if arraydimension > 0:
					for i in array2list(arraydimension, field[1]):
						newrow.append(tuple([rownum] + i))
					
				elif col_defs[fieldname][0] == 'EntityRef':
					newrow.append(tuple([rownum] + [field[0]['EntityRef', 1][2]['entityId']]))
				else:
					newrow.append(tuple([rownum] + [field[1]]))
				if rown != None:
					return(newrow)
			else:
				return([tuple()])
			pass
		else:
			if newrow == []:
				return([tuple()])
			else:
				return(newrow)
		rownum = rownum + 1

def xdict2fields(xdict):
	tablename = tuple(xdict.keys())[0][0]
	fields = set()
	n = 1
	while True:
		if ('row', n) in xdict[(tablename, 1)][0]:
			row = xdict[(tablename, 1)][0][('row', n)]
			for r in row:
				for f in r:
					fields.add(f[0])
		elif ('Attributes', 1) in xdict[(tablename, 1)][0]:
			for i in c.xdict[(tablename, 1)][0][('Attributes', 1)][0].keys():
				fields.add(i[0])
			break
		else:
			break
		n = n + 1
	fields = list(fields)
	fields.sort()
	return(tuple(fields))

# Section: Main FX

global oratables_map # Warning: this could be outdated for cycle > 4
oratables_map = {
	"ACAPolarization": "XML_ACAPOLARIZATION_ENTITIES",
	"AccumMode": "XML_ACCUMMODE_ENTITIES",
	"ACSAlarmMessage": "XML_ACSALARMMESSAGE_ENTITIES",
	"AcsCommandCenterProject": "XML_ACSCOMMANDCENTERP_ENTITIES",
	"AcsCommandCenterTools": "XML_ACSCOMMANDCENTERT_ENTITIES",
	"ACSError": "XML_ACSERROR_ENTITIES",
	"ACSLogTS": "XML_ACSLOGTS_ENTITIES",
	"Address": "XML_ADDRESS_ENTITIES",
	"AlmaRadiometerTable": "XML_ALMARADIOMETERTAB_ENTITIES",
	"AnnotationTable": "XML_ANNOTATIONTABLE_ENTITIES",
	"AntennaMake": "XML_ANTENNAMAKE_ENTITIES",
	"AntennaMotionPattern": "XML_ANTENNAMOTIONPATT_ENTITIES",
	"AntennaTable": "XML_ANTENNATABLE_ENTITIES",
	"AntennaType": "XML_ANTENNATYPE_ENTITIES",
	"ASDM": "XML_ASDM_ENTITIES",
	"ASDMBinaryTable": "XML_ASDMBINARYTABLE_ENTITIES",
	"ASIConfiguration": "XML_ASICONFIGURATION_ENTITIES",
	"ASIMessage": "XML_ASIMESSAGE_ENTITIES",
	"AssociatedCalNature": "XML_ASSOCIATEDCALNATU_ENTITIES",
	"AssociatedFieldNature": "XML_ASSOCIATEDFIELDNA_ENTITIES",
	"AtmPhaseCorrection": "XML_ATMPHASECORRECTIO_ENTITIES",
	"AxisName": "XML_AXISNAME_ENTITIES",
	"BasebandName": "XML_BASEBANDNAME_ENTITIES",
	"BaselineReferenceCode": "XML_BASELINEREFERENCE_ENTITIES",
	"bulkTest": "XML_BULKTEST_ENTITIES",
	"CalAmpliTable": "XML_CALAMPLITABLE_ENTITIES",
	"CalAtmosphereTable": "XML_CALATMOSPHERETABL_ENTITIES",
	"CalBandpassTable": "XML_CALBANDPASSTABLE_ENTITIES",
	"CalCurveTable": "XML_CALCURVETABLE_ENTITIES",
	"CalCurveType": "XML_CALCURVETYPE_ENTITIES",
	"CalDataOrigin": "XML_CALDATAORIGIN_ENTITIES",
	"CalDataTable": "XML_CALDATATABLE_ENTITIES",
	"CalDelayTable": "XML_CALDELAYTABLE_ENTITIES",
	"CalDeviceTable": "XML_CALDEVICETABLE_ENTITIES",
	"CalFluxTable": "XML_CALFLUXTABLE_ENTITIES",
	"CalFocusModelTable": "XML_CALFOCUSMODELTABL_ENTITIES",
	"CalFocusTable": "XML_CALFOCUSTABLE_ENTITIES",
	"CalGainTable": "XML_CALGAINTABLE_ENTITIES",
	"CalHolographyTable": "XML_CALHOLOGRAPHYTABL_ENTITIES",
	"CalibrationDevice": "XML_CALIBRATIONDEVICE_ENTITIES",
	"CalibrationFunction": "XML_CALIBRATIONFUNCTI_ENTITIES",
	"CalibrationMode": "XML_CALIBRATIONMODE_ENTITIES",
	"CalibrationSet": "XML_CALIBRATIONSET_ENTITIES",
	"CalPhaseTable": "XML_CALPHASETABLE_ENTITIES",
	"CalPointingModelTable": "XML_CALPOINTINGMODELT_ENTITIES",
	"CalPointingTable": "XML_CALPOINTINGTABLE_ENTITIES",
	"CalPositionTable": "XML_CALPOSITIONTABLE_ENTITIES",
	"CalPrimaryBeamTable": "XML_CALPRIMARYBEAMTAB_ENTITIES",
	"CalQueryParameters": "XML_CALQUERYPARAMETER_ENTITIES",
	"CalReductionTable": "XML_CALREDUCTIONTABLE_ENTITIES",
	"CalSeeingTable": "XML_CALSEEINGTABLE_ENTITIES",
	"CalType": "XML_CALTYPE_ENTITIES",
	"CalWVRTable": "XML_CALWVRTABLE_ENTITIES",
	"CommonEntity": "XML_COMMONENTITY_ENTITIES",
	"commontypes": "XML_COMMONTYPES_ENTITIES",
	"ConfigDescriptionTable": "XML_CONFIGDESCRIPTION_ENTITIES",
	"CorrelationBit": "XML_CORRELATIONBIT_ENTITIES",
	"CorrelationMode": "XML_CORRELATIONMODE_ENTITIES",
	"CorrelatorCalibration": "XML_CORRELATORCALIBRA_ENTITIES",
	"CorrelatorModeTable": "XML_CORRELATORMODETAB_ENTITIES",
	"CorrelatorName": "XML_CORRELATORNAME_ENTITIES",
	"CorrelatorType": "XML_CORRELATORTYPE_ENTITIES",
	"DataContent": "XML_DATACONTENT_ENTITIES",
	"DataDescriptionTable": "XML_DATADESCRIPTIONTA_ENTITIES",
	"DataScale": "XML_DATASCALE_ENTITIES",
	"DelayModelTable": "XML_DELAYMODELTABLE_ENTITIES",
	"DetectorBandType": "XML_DETECTORBANDTYPE_ENTITIES",
	"DirectionReferenceCode": "XML_DIRECTIONREFERENC_ENTITIES",
	"DopplerReferenceCode": "XML_DOPPLERREFERENCEC_ENTITIES",
	"DopplerTable": "XML_DOPPLERTABLE_ENTITIES",
	"DopplerTrackingMode": "XML_DOPPLERTRACKINGMO_ENTITIES",
	"EphemerisTable": "XML_EPHEMERISTABLE_ENTITIES",
	"ExecBlockTable": "XML_EXECBLOCKTABLE_ENTITIES",
	"ExecConfig": "XML_EXECCONFIG_ENTITIES",
	"FeedTable": "XML_FEEDTABLE_ENTITIES",
	"FieldCode": "XML_FIELDCODE_ENTITIES",
	"FieldTable": "XML_FIELDTABLE_ENTITIES",
	"FilterMode": "XML_FILTERMODE_ENTITIES",
	"FlagCmdTable": "XML_FLAGCMDTABLE_ENTITIES",
	"FlagTable": "XML_FLAGTABLE_ENTITIES",
	"FluxCalibrationMethod": "XML_FLUXCALIBRATIONME_ENTITIES",
	"FocusMethod": "XML_FOCUSMETHOD_ENTITIES",
	"FocusModelTable": "XML_FOCUSMODELTABLE_ENTITIES",
	"FocusTable": "XML_FOCUSTABLE_ENTITIES",
	"FreqOffsetTable": "XML_FREQOFFSETTABLE_ENTITIES",
	"FrequencyReferenceCode": "XML_FREQUENCYREFERENC_ENTITIES",
	"GainTrackingTable": "XML_GAINTRACKINGTABLE_ENTITIES",
	"HistoryTable": "XML_HISTORYTABLE_ENTITIES",
	"HolographyChannelType": "XML_HOLOGRAPHYCHANNEL_ENTITIES",
	"HolographyTable": "XML_HOLOGRAPHYTABLE_ENTITIES",
	"IdentifierRange": "XML_IDENTIFIERRANGE_ENTITIES",
	"InvalidatingCondition": "XML_INVALIDATINGCONDI_ENTITIES",
	"loggingMI": "XML_LOGGINGMI_ENTITIES",
	"MainTable": "XML_MAINTABLE_ENTITIES",
	"NetSideband": "XML_NETSIDEBAND_ENTITIES",
	"ObsAttachment": "XML_OBSATTACHMENT_ENTITIES",
	"ObservationTable": "XML_OBSERVATIONTABLE_ENTITIES",
	"ObservingControlScript": "XML_OBSERVINGCONTROLS_ENTITIES",
	"ObservingMode": "XML_OBSERVINGMODE_ENTITIES",
	"ObsProject": "XML_OBSPROJECT_ENTITIES",
	"ObsProposal": "XML_OBSPROPOSAL_ENTITIES",
	"ObsReview": "XML_OBSREVIEW_ENTITIES",
	"ObsToolUserPrefs": "XML_OBSTOOLUSERPREFS_ENTITIES",
	"OUSStatus": "XML_OUSSTATUS_ENTITIES",
	"PointingMethod": "XML_POINTINGMETHOD_ENTITIES",
	"PointingModelMode": "XML_POINTINGMODELMODE_ENTITIES",
	"PointingModelTable": "XML_POINTINGMODELTABL_ENTITIES",
	"PointingTable": "XML_POINTINGTABLE_ENTITIES",
	"PolarizationTable": "XML_POLARIZATIONTABLE_ENTITIES",
	"PolarizationType": "XML_POLARIZATIONTYPE_ENTITIES",
	"PositionMethod": "XML_POSITIONMETHOD_ENTITIES",
	"PositionReferenceCode": "XML_POSITIONREFERENCE_ENTITIES",
	"Preferences": "XML_PREFERENCES_ENTITIES",
	"PrimaryBeamDescription": "XML_PRIMARYBEAMDESCRI_ENTITIES",
	"PrimitiveDataType": "XML_PRIMITIVEDATATYPE_ENTITIES",
	"ProcessorSubType": "XML_PROCESSORSUBTYPE_ENTITIES",
	"ProcessorTable": "XML_PROCESSORTABLE_ENTITIES",
	"ProcessorType": "XML_PROCESSORTYPE_ENTITIES",
	"ProjectStatus": "XML_PROJECTSTATUS_ENTITIES",
	"pset": "XML_PSET_ENTITIES",
	"psetdef": "XML_PSETDEF_ENTITIES",
	"QlAtmosphereSummary": "XML_QLATMOSPHERESUMMA_ENTITIES",
	"QlFocusSummary": "XML_QLFOCUSSUMMARY_ENTITIES",
	"QlPointingSummary": "XML_QLPOINTINGSUMMARY_ENTITIES",
	"QuickLookDisplay": "XML_QUICKLOOKDISPLAYX_ENTITIES",
	"QuickLookDisplayX": "XML_QUICKLOOKDISPLAY_ENTITIES",
	"QuickLookResult": "XML_QUICKLOOKRESULT_ENTITIES",
	"QuickLookSummary": "XML_QUICKLOOKSUMMARY_ENTITIES",
	"RadialVelocityReferenceCode": "XML_RADIALVELOCITYREF_ENTITIES",
	"ReceiverBand": "XML_RECEIVERBAND_ENTITIES",
	"ReceiverSideband": "XML_RECEIVERSIDEBAND_ENTITIES",
	"ReceiverTable": "XML_RECEIVERTABLE_ENTITIES",
	"SBStatus": "XML_SBSTATUS_ENTITIES",
	"SBSummaryTable": "XML_SBSUMMARYTABLE_ENTITIES",
	"SBType": "XML_SBTYPE_ENTITIES",
	"ScaleTable": "XML_SCALETABLE_ENTITIES",
	"ScanIntent": "XML_SCANINTENT_ENTITIES",
	"ScanTable": "XML_SCANTABLE_ENTITIES",
	"SchedBlock": "XML_SCHEDBLOCK_ENTITIES",
	"SchedulerMode": "XML_SCHEDULERMODE_ENTITIES",
	"SchedulingPolicy": "XML_SCHEDULINGPOLICY_ENTITIES",
	"SciPipeResults": "XML_SCIPIPERESULTS_ENTITIES",
	"sdmDataHeader": "XML_SDMDATAHEADER_ENTITIES",
	"SeeingTable": "XML_SEEINGTABLE_ENTITIES",
	"SidebandProcessingMode": "XML_SIDEBANDPROCESSIN_ENTITIES",
	"SourceModel": "XML_SOURCEMODEL_ENTITIES",
	"SourceTable": "XML_SOURCETABLE_ENTITIES",
	"SpecialSB": "XML_SPECIALSB_ENTITIES",
	"SpectralResolutionType": "XML_SPECTRALRESOLUTIO_ENTITIES",
	"SpectralWindowTable": "XML_SPECTRALWINDOWTAB_ENTITIES",
	"SquareLawDetectorTable": "XML_SQUARELAWDETECTOR_ENTITIES",
	"StateTable": "XML_STATETABLE_ENTITIES",
	"StationTable": "XML_STATIONTABLE_ENTITIES",
	"StationType": "XML_STATIONTYPE_ENTITIES",
	"StokesParameter": "XML_STOKESPARAMETER_ENTITIES",
	"SubscanFieldSource": "XML_SUBSCANFIELDSOURC_ENTITIES",
	"SubscanIntent": "XML_SUBSCANINTENT_ENTITIES",
	"SubscanSpectralSpec": "XML_SUBSCANSPECTRALSP_ENTITIES",
	"SubscanTable": "XML_SUBSCANTABLE_ENTITIES",
	"SwitchCycleTable": "XML_SWITCHCYCLETABLE_ENTITIES",
	"SwitchingMode": "XML_SWITCHINGMODE_ENTITIES",
	"SyscalMethod": "XML_SYSCALMETHOD_ENTITIES",
	"SysCalTable": "XML_SYSCALTABLE_ENTITIES",
	"TestObsProject": "XML_TESTOBSPROJECT_ENTITIES",
	"TestObsProposal": "XML_TESTOBSPROPOSAL_ENTITIES",
	"TestSchedBlock": "XML_TESTSCHEDBLOCK_ENTITIES",
	"TestValueTypes": "XML_TESTVALUETYPES_ENTITIES",
	"TimeSampling": "XML_TIMESAMPLING_ENTITIES",
	"TimeScale": "XML_TIMESCALE_ENTITIES",
	"TotalPowerTable": "XML_TOTALPOWERTABLE_ENTITIES",
	"User": "XML_USER_ENTITIES",
	"ValueTypes": "XML_VALUETYPES_ENTITIES",
	"WeatherTable": "XML_WEATHERTABLE_ENTITIES",
	"WeightType": "XML_WEIGHTTYPE_ENTITIES",
	"WindowFunction": "XML_WINDOWFUNCTION_ENTITIES",
	"WVMCalTable": "XML_WVMCALTABLE_ENTITIES",
	"WVRMethod": "XML_WVRMETHOD_ENTITIES"}

global datatypes_map # Warning: this could be outdated for ALMA Cycle > 4
datatypes_map = {"AccumMode": "character varying(64)", 
	"Angle": "binary_double", 
	"AngularRate": "binary_double", 
	"AntennaMake": "character varying(64)", 
	"AntennaMotionPattern": "character varying(64)", 
	"AntennaType": "character varying(64)", 
	"ArrayTime": "integer", 
	"ArrayTimeInterval": "character varying(64)", 
	"AssociatedCalNature": "character varying(64)", 
	"AtmPhaseCorrection": "character varying(64)", 
	"AxisName": "character varying(64)", 
	"BasebandName": "character varying(64)", 
	"boolean": "character varying(8)", 
	"CalCurveType": "character varying(64)", 
	"CalDataOrigin": "character varying(64)", 
	"CalibrationDevice": "character varying(64)", 
	"CalibrationFunction": "character varying(64)", 
	"CalibrationSet": "character varying(64)", 
	"CalType": "character varying(64)", 
	"Complex": "character varying(64)", 
	"CorrelationBit": "character varying(64)", 
	"CorrelationMode": "character varying(64)", 
	"CorrelatorCalibration": "character varying(64)", 
	"CorrelatorName": "character varying(64)", 
	"DataScale": "character varying(64)", 
	"DetectorBandType": "character varying(64)", 
	"DirectionReferenceCode": "character varying(64)", 
	"DopplerReferenceCode": "character varying(64)", 
	"double": "binary_double", 
	"EntityRef": "character varying(33)", 
	"FilterMode": "character varying(64)", 
	"float": "binary_double", 
	"Flux": "character varying(64)", 
	"FluxCalibrationMethod": "character varying(64)", 
	"FocusMethod": "character varying(64)", 
	"Frequency": "binary_double", 
	"FrequencyReferenceCode": "character varying(64)", 
	"HolographyChannelType": "character varying(64)", 
	"Humidity": "binary_double", 
	"int": "integer", 
	"Interval": "integer", 
	"InvalidatingCondition": "character varying(64)", 
	"Length": "binary_double", 
	"long": "binary_double", 
	"NetSideband": "character varying(64)", 
	"nnERMAv3": "character varying(512)", 
	"PointingMethod": "character varying(64)", 
	"PointingModelMode": "character varying(64)", 
	"PolarizationType": "character varying(64)", 
	"PositionMethod": "character varying(64)", 
	"Pressure": "binary_double", 
	"PrimaryBeamDescription": "character varying(64)", 
	"ProcessorSubType": "character varying(64)", 
	"ProcessorType": "character varying(64)", 
	"RadialVelocityReferenceCode": "character varying(64)", 
	"ReceiverBand": "character varying(64)", 
	"ReceiverSideband": "character varying(64)", 
	"SBType": "character varying(64)", 
	"ScanIntent": "character varying(64)", 
	"SidebandProcessingMode": "character varying(64)", 
	"SourceModel": "character varying(64)", 
	"SpectralResolutionType": "character varying(64)", 
	"Speed": "binary_double", 
	"StationType": "character varying(64)", 
	"StokesParameter": "character varying(64)", 
	"String": "character varying(256)", 
	"SubscanIntent": "character varying(64)", 
	"SwitchingMode": "character varying(64)", 
	"SyscalMethod": "character varying(64)", 
	"Tag": "character varying(64)", 
	"Temperature": "binary_double", 
	"TimeSampling": "character varying(64)", 
	"TimeScale": "character varying(64)", 
	"timestamp": "timestamp", 
	"WeightType": "character varying(64)", 
	"WindowFunction": "character varying(64)", 
	"WVRMethod": "character varying(64)"}

global asdm_datamodel # Warning: This could be outdated for ALMA Cycle > 4
asdm_datamodel = [
('XML_ALMARADIOMETERTAB_ENTITIES', 'AlmaRadiometerTable', 'almaRadiometerId', 'Tag', 0, 'a', 'c'),
('XML_ALMARADIOMETERTAB_ENTITIES', 'AlmaRadiometerTable', 'numAntenna', 'int', 0, 'none', 'd'),
('XML_ALMARADIOMETERTAB_ENTITIES', 'AlmaRadiometerTable', 'spectralWindowId', 'Tag', 1, 'b', 'd'),
('XML_ANNOTATIONTABLE_ENTITIES', 'AnnotationTable', 'annotationId', 'Tag', 0, 'a', 'c'),
('XML_ANNOTATIONTABLE_ENTITIES', 'AnnotationTable', 'antennaId', 'Tag', 1, 'b', 'd'),
('XML_ANNOTATIONTABLE_ENTITIES', 'AnnotationTable', 'basebandName', 'BasebandName', 0, 'none', 'd'),
('XML_ANNOTATIONTABLE_ENTITIES', 'AnnotationTable', 'details', 'String', 0, 'none', 'c'),
('XML_ANNOTATIONTABLE_ENTITIES', 'AnnotationTable', 'dValue', 'double', 0, 'none', 'd'),
('XML_ANNOTATIONTABLE_ENTITIES', 'AnnotationTable', 'interval', 'Interval', 0, 'none', 'd'),
('XML_ANNOTATIONTABLE_ENTITIES', 'AnnotationTable', 'issue', 'String', 0, 'none', 'c'),
('XML_ANNOTATIONTABLE_ENTITIES', 'AnnotationTable', 'llValue', 'long', 0, 'none', 'd'),
('XML_ANNOTATIONTABLE_ENTITIES', 'AnnotationTable', 'numAntenna', 'int', 0, 'none', 'd'),
('XML_ANNOTATIONTABLE_ENTITIES', 'AnnotationTable', 'numBaseband', 'int', 0, 'none', 'd'),
('XML_ANNOTATIONTABLE_ENTITIES', 'AnnotationTable', 'time', 'ArrayTime', 0, 'none', 'c'),
('XML_ANNOTATIONTABLE_ENTITIES', 'AnnotationTable', 'vdValue', 'double', 1, 'none', 'd'),
('XML_ANNOTATIONTABLE_ENTITIES', 'AnnotationTable', 'vllValue', 'long', 1, 'none', 'd'),
('XML_ANNOTATIONTABLE_ENTITIES', 'AnnotationTable', 'vvdValues', 'double', 2, 'none', 'd'),
('XML_ANNOTATIONTABLE_ENTITIES', 'AnnotationTable', 'vvllValue', 'long', 2, 'none', 'd'),
('XML_ANTENNATABLE_ENTITIES', 'AntennaTable', 'antennaId', 'Tag', 0, 'a', 'c'),
('XML_ANTENNATABLE_ENTITIES', 'AntennaTable', 'antennaMake', 'AntennaMake', 0, 'none', 'c'),
('XML_ANTENNATABLE_ENTITIES', 'AntennaTable', 'antennaType', 'AntennaType', 0, 'none', 'c'),
('XML_ANTENNATABLE_ENTITIES', 'AntennaTable', 'assocAntennaId', 'Tag', 0, 'b', 'd'),
('XML_ANTENNATABLE_ENTITIES', 'AntennaTable', 'dishDiameter', 'Length', 0, 'none', 'c'),
('XML_ANTENNATABLE_ENTITIES', 'AntennaTable', 'name', 'String', 0, 'none', 'c'),
('XML_ANTENNATABLE_ENTITIES', 'AntennaTable', 'offset', 'Length', 1, 'none', 'c'),
('XML_ANTENNATABLE_ENTITIES', 'AntennaTable', 'position', 'Length', 1, 'none', 'c'),
('XML_ANTENNATABLE_ENTITIES', 'AntennaTable', 'stationId', 'Tag', 0, 'b', 'c'),
('XML_ANTENNATABLE_ENTITIES', 'AntennaTable', 'time', 'ArrayTime', 0, 'none', 'c'),
('XML_CALAMPLITABLE_ENTITIES', 'CalAmpliTable', 'antennaName', 'String', 0, 'none', 'c'),
('XML_CALAMPLITABLE_ENTITIES', 'CalAmpliTable', 'apertureEfficiency', 'float', 1, 'none', 'c'),
('XML_CALAMPLITABLE_ENTITIES', 'CalAmpliTable', 'apertureEfficiencyError', 'float', 1, 'none', 'c'),
('XML_CALAMPLITABLE_ENTITIES', 'CalAmpliTable', 'atmPhaseCorrection', 'AtmPhaseCorrection', 0, 'none', 'c'),
('XML_CALAMPLITABLE_ENTITIES', 'CalAmpliTable', 'basebandName', 'BasebandName', 0, 'none', 'd'),
('XML_CALAMPLITABLE_ENTITIES', 'CalAmpliTable', 'calDataId', 'Tag', 0, 'b', 'c'),
('XML_CALAMPLITABLE_ENTITIES', 'CalAmpliTable', 'calReductionId', 'Tag', 0, 'b', 'c'),
('XML_CALAMPLITABLE_ENTITIES', 'CalAmpliTable', 'correctionValidity', 'boolean', 0, 'none', 'd'),
('XML_CALAMPLITABLE_ENTITIES', 'CalAmpliTable', 'endValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALAMPLITABLE_ENTITIES', 'CalAmpliTable', 'frequencyRange', 'Frequency', 1, 'none', 'c'),
('XML_CALAMPLITABLE_ENTITIES', 'CalAmpliTable', 'numReceptor', 'int', 0, 'none', 'c'),
('XML_CALAMPLITABLE_ENTITIES', 'CalAmpliTable', 'polarizationTypes', 'PolarizationType', 1, 'none', 'c'),
('XML_CALAMPLITABLE_ENTITIES', 'CalAmpliTable', 'receiverBand', 'ReceiverBand', 0, 'none', 'c'),
('XML_CALAMPLITABLE_ENTITIES', 'CalAmpliTable', 'startValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'alphaSpectrum', 'float', 2, 'none', 'd'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'antennaName', 'String', 0, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'basebandName', 'BasebandName', 0, 'none', 'd'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'calDataId', 'Tag', 0, 'b', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'calReductionId', 'Tag', 0, 'b', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'endValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'forwardEfficiency', 'float', 1, 'none', 'd'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'forwardEfficiencyError', 'double', 1, 'none', 'd'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'forwardEffSpectrum', 'float', 2, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'frequencyRange', 'Frequency', 1, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'frequencySpectrum', 'Frequency', 1, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'groundPressure', 'Pressure', 0, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'groundRelHumidity', 'Humidity', 0, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'groundTemperature', 'Temperature', 0, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'numFreq', 'int', 0, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'numLoad', 'int', 0, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'numReceptor', 'int', 0, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'polarizationTypes', 'PolarizationType', 1, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'powerLoadSpectrum', 'float', 3, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'powerSkySpectrum', 'float', 2, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'receiverBand', 'ReceiverBand', 0, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'sbGain', 'float', 1, 'none', 'd'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'sbGainError', 'float', 1, 'none', 'd'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'sbGainSpectrum', 'float', 2, 'none', 'd'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'startValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'syscalType', 'SyscalMethod', 0, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'tAtm', 'Temperature', 1, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'tAtmSpectrum', 'Temperature', 2, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'tau', 'float', 1, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'tauSpectrum', 'float', 2, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'tRec', 'Temperature', 1, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'tRecSpectrum', 'Temperature', 2, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'tSys', 'Temperature', 1, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'tSysSpectrum', 'Temperature', 2, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'water', 'Length', 1, 'none', 'c'),
('XML_CALATMOSPHERETABL_ENTITIES', 'CalAtmosphereTable', 'waterError', 'Length', 1, 'none', 'c'),
('XML_CALBANDPASSTABLE_ENTITIES', 'CalBandpassTable', 'antennaNames', 'String', 1, 'none', 'c'),
('XML_CALBANDPASSTABLE_ENTITIES', 'CalBandpassTable', 'atmPhaseCorrection', 'AtmPhaseCorrection', 0, 'none', 'c'),
('XML_CALBANDPASSTABLE_ENTITIES', 'CalBandpassTable', 'basebandName', 'BasebandName', 0, 'none', 'c'),
('XML_CALBANDPASSTABLE_ENTITIES', 'CalBandpassTable', 'calDataId', 'Tag', 0, 'b', 'c'),
('XML_CALBANDPASSTABLE_ENTITIES', 'CalBandpassTable', 'calReductionId', 'Tag', 0, 'b', 'c'),
('XML_CALBANDPASSTABLE_ENTITIES', 'CalBandpassTable', 'curve', 'float', 3, 'none', 'c'),
('XML_CALBANDPASSTABLE_ENTITIES', 'CalBandpassTable', 'endValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALBANDPASSTABLE_ENTITIES', 'CalBandpassTable', 'freqLimits', 'Frequency', 1, 'none', 'c'),
('XML_CALBANDPASSTABLE_ENTITIES', 'CalBandpassTable', 'numAntenna', 'int', 0, 'none', 'c'),
('XML_CALBANDPASSTABLE_ENTITIES', 'CalBandpassTable', 'numBaseline', 'int', 0, 'none', 'd'),
('XML_CALBANDPASSTABLE_ENTITIES', 'CalBandpassTable', 'numPoly', 'int', 0, 'none', 'c'),
('XML_CALBANDPASSTABLE_ENTITIES', 'CalBandpassTable', 'numReceptor', 'int', 0, 'none', 'c'),
('XML_CALBANDPASSTABLE_ENTITIES', 'CalBandpassTable', 'polarizationTypes', 'PolarizationType', 1, 'none', 'c'),
('XML_CALBANDPASSTABLE_ENTITIES', 'CalBandpassTable', 'receiverBand', 'ReceiverBand', 0, 'none', 'c'),
('XML_CALBANDPASSTABLE_ENTITIES', 'CalBandpassTable', 'reducedChiSquared', 'double', 1, 'none', 'c'),
('XML_CALBANDPASSTABLE_ENTITIES', 'CalBandpassTable', 'refAntennaName', 'String', 0, 'none', 'c'),
('XML_CALBANDPASSTABLE_ENTITIES', 'CalBandpassTable', 'rms', 'float', 2, 'none', 'd'),
('XML_CALBANDPASSTABLE_ENTITIES', 'CalBandpassTable', 'sideband', 'NetSideband', 0, 'none', 'c'),
('XML_CALBANDPASSTABLE_ENTITIES', 'CalBandpassTable', 'startValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALBANDPASSTABLE_ENTITIES', 'CalBandpassTable', 'typeCurve', 'CalCurveType', 0, 'none', 'c'),
('XML_CALCURVETABLE_ENTITIES', 'CalCurveTable', 'antennaNames', 'String', 1, 'none', 'c'),
('XML_CALCURVETABLE_ENTITIES', 'CalCurveTable', 'atmPhaseCorrection', 'AtmPhaseCorrection', 0, 'none', 'c'),
('XML_CALCURVETABLE_ENTITIES', 'CalCurveTable', 'calDataId', 'Tag', 0, 'b', 'c'),
('XML_CALCURVETABLE_ENTITIES', 'CalCurveTable', 'calReductionId', 'Tag', 0, 'b', 'c'),
('XML_CALCURVETABLE_ENTITIES', 'CalCurveTable', 'curve', 'float', 3, 'none', 'c'),
('XML_CALCURVETABLE_ENTITIES', 'CalCurveTable', 'endValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALCURVETABLE_ENTITIES', 'CalCurveTable', 'frequencyRange', 'Frequency', 1, 'none', 'c'),
('XML_CALCURVETABLE_ENTITIES', 'CalCurveTable', 'numAntenna', 'int', 0, 'none', 'c'),
('XML_CALCURVETABLE_ENTITIES', 'CalCurveTable', 'numBaseline', 'int', 0, 'none', 'd'),
('XML_CALCURVETABLE_ENTITIES', 'CalCurveTable', 'numPoly', 'int', 0, 'none', 'c'),
('XML_CALCURVETABLE_ENTITIES', 'CalCurveTable', 'numReceptor', 'int', 0, 'none', 'c'),
('XML_CALCURVETABLE_ENTITIES', 'CalCurveTable', 'polarizationTypes', 'PolarizationType', 1, 'none', 'c'),
('XML_CALCURVETABLE_ENTITIES', 'CalCurveTable', 'receiverBand', 'ReceiverBand', 0, 'none', 'c'),
('XML_CALCURVETABLE_ENTITIES', 'CalCurveTable', 'reducedChiSquared', 'double', 1, 'none', 'c'),
('XML_CALCURVETABLE_ENTITIES', 'CalCurveTable', 'refAntennaName', 'String', 0, 'none', 'c'),
('XML_CALCURVETABLE_ENTITIES', 'CalCurveTable', 'rms', 'float', 2, 'none', 'd'),
('XML_CALCURVETABLE_ENTITIES', 'CalCurveTable', 'startValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALCURVETABLE_ENTITIES', 'CalCurveTable', 'typeCurve', 'CalCurveType', 0, 'none', 'c'),
('XML_CALDATATABLE_ENTITIES', 'CalDataTable', 'assocCalDataId', 'Tag', 0, 'b', 'd'),
('XML_CALDATATABLE_ENTITIES', 'CalDataTable', 'assocCalNature', 'AssociatedCalNature', 0, 'none', 'd'),
('XML_CALDATATABLE_ENTITIES', 'CalDataTable', 'calDataId', 'Tag', 0, 'a', 'c'),
('XML_CALDATATABLE_ENTITIES', 'CalDataTable', 'calDataType', 'CalDataOrigin', 0, 'none', 'c'),
('XML_CALDATATABLE_ENTITIES', 'CalDataTable', 'calType', 'CalType', 0, 'none', 'c'),
('XML_CALDATATABLE_ENTITIES', 'CalDataTable', 'endTimeObserved', 'ArrayTime', 0, 'none', 'c'),
('XML_CALDATATABLE_ENTITIES', 'CalDataTable', 'execBlockUID', 'EntityRef', 0, 'none', 'c'),
('XML_CALDATATABLE_ENTITIES', 'CalDataTable', 'fieldName', 'String', 1, 'none', 'd'),
('XML_CALDATATABLE_ENTITIES', 'CalDataTable', 'numScan', 'int', 0, 'none', 'c'),
('XML_CALDATATABLE_ENTITIES', 'CalDataTable', 'scanIntent', 'ScanIntent', 1, 'none', 'd'),
('XML_CALDATATABLE_ENTITIES', 'CalDataTable', 'scanSet', 'int', 1, 'none', 'c'),
('XML_CALDATATABLE_ENTITIES', 'CalDataTable', 'sourceCode', 'String', 1, 'none', 'd'),
('XML_CALDATATABLE_ENTITIES', 'CalDataTable', 'sourceName', 'String', 1, 'none', 'd'),
('XML_CALDATATABLE_ENTITIES', 'CalDataTable', 'startTimeObserved', 'ArrayTime', 0, 'none', 'c'),
('XML_CALDELAYTABLE_ENTITIES', 'CalDelayTable', 'antennaName', 'String', 0, 'none', 'c'),
('XML_CALDELAYTABLE_ENTITIES', 'CalDelayTable', 'appliedDelay', 'double', 1, 'none', 'c'),
('XML_CALDELAYTABLE_ENTITIES', 'CalDelayTable', 'atmPhaseCorrection', 'AtmPhaseCorrection', 0, 'none', 'c'),
('XML_CALDELAYTABLE_ENTITIES', 'CalDelayTable', 'basebandName', 'BasebandName', 0, 'none', 'c'),
('XML_CALDELAYTABLE_ENTITIES', 'CalDelayTable', 'calDataId', 'Tag', 0, 'b', 'c'),
('XML_CALDELAYTABLE_ENTITIES', 'CalDelayTable', 'calReductionId', 'Tag', 0, 'b', 'c'),
('XML_CALDELAYTABLE_ENTITIES', 'CalDelayTable', 'crossDelayOffset', 'double', 0, 'none', 'd'),
('XML_CALDELAYTABLE_ENTITIES', 'CalDelayTable', 'crossDelayOffsetError', 'double', 0, 'none', 'd'),
('XML_CALDELAYTABLE_ENTITIES', 'CalDelayTable', 'delayError', 'double', 1, 'none', 'c'),
('XML_CALDELAYTABLE_ENTITIES', 'CalDelayTable', 'delayOffset', 'double', 1, 'none', 'c'),
('XML_CALDELAYTABLE_ENTITIES', 'CalDelayTable', 'endValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALDELAYTABLE_ENTITIES', 'CalDelayTable', 'numReceptor', 'int', 0, 'none', 'c'),
('XML_CALDELAYTABLE_ENTITIES', 'CalDelayTable', 'numSideband', 'int', 0, 'none', 'd'),
('XML_CALDELAYTABLE_ENTITIES', 'CalDelayTable', 'polarizationTypes', 'PolarizationType', 1, 'none', 'c'),
('XML_CALDELAYTABLE_ENTITIES', 'CalDelayTable', 'receiverBand', 'ReceiverBand', 0, 'none', 'c'),
('XML_CALDELAYTABLE_ENTITIES', 'CalDelayTable', 'reducedChiSquared', 'double', 1, 'none', 'c'),
('XML_CALDELAYTABLE_ENTITIES', 'CalDelayTable', 'refAntennaName', 'String', 0, 'none', 'c'),
('XML_CALDELAYTABLE_ENTITIES', 'CalDelayTable', 'refFreq', 'Frequency', 1, 'none', 'd'),
('XML_CALDELAYTABLE_ENTITIES', 'CalDelayTable', 'refFreqPhase', 'Angle', 1, 'none', 'd'),
('XML_CALDELAYTABLE_ENTITIES', 'CalDelayTable', 'sidebands', 'ReceiverSideband', 1, 'none', 'd'),
('XML_CALDELAYTABLE_ENTITIES', 'CalDelayTable', 'startValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALDEVICETABLE_ENTITIES', 'CalDeviceTable', 'antennaId', 'Tag', 0, 'b', 'c'),
('XML_CALDEVICETABLE_ENTITIES', 'CalDeviceTable', 'calEff', 'float', 2, 'none', 'd'),
('XML_CALDEVICETABLE_ENTITIES', 'CalDeviceTable', 'calLoadNames', 'CalibrationDevice', 0, 'none', 'c'),
('XML_CALDEVICETABLE_ENTITIES', 'CalDeviceTable', 'feedId', 'int', 0, 'b', 'c'),
('XML_CALDEVICETABLE_ENTITIES', 'CalDeviceTable', 'noiseCal', 'double', 1, 'none', 'd'),
('XML_CALDEVICETABLE_ENTITIES', 'CalDeviceTable', 'numCalload', 'int', 0, 'none', 'c'),
('XML_CALDEVICETABLE_ENTITIES', 'CalDeviceTable', 'numReceptor', 'int', 0, 'none', 'd'),
('XML_CALDEVICETABLE_ENTITIES', 'CalDeviceTable', 'spectralWindowId', 'Tag', 0, 'b', 'c'),
('XML_CALDEVICETABLE_ENTITIES', 'CalDeviceTable', 'temperatureLoad', 'Temperature', 1, 'none', 'd'),
('XML_CALDEVICETABLE_ENTITIES', 'CalDeviceTable', 'timeInterval', 'ArrayTimeInterval', 0, 'none', 'c'),
('XML_CALFLUXTABLE_ENTITIES', 'CalFluxTable', 'calDataId', 'Tag', 0, 'b', 'c'),
('XML_CALFLUXTABLE_ENTITIES', 'CalFluxTable', 'calReductionId', 'Tag', 0, 'b', 'c'),
('XML_CALFLUXTABLE_ENTITIES', 'CalFluxTable', 'direction', 'Angle', 1, 'none', 'd'),
('XML_CALFLUXTABLE_ENTITIES', 'CalFluxTable', 'directionCode', 'DirectionReferenceCode', 0, 'none', 'd'),
('XML_CALFLUXTABLE_ENTITIES', 'CalFluxTable', 'directionEquinox', 'Angle', 0, 'none', 'd'),
('XML_CALFLUXTABLE_ENTITIES', 'CalFluxTable', 'endValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALFLUXTABLE_ENTITIES', 'CalFluxTable', 'flux', 'double', 2, 'none', 'c'),
('XML_CALFLUXTABLE_ENTITIES', 'CalFluxTable', 'fluxError', 'double', 2, 'none', 'c'),
('XML_CALFLUXTABLE_ENTITIES', 'CalFluxTable', 'fluxMethod', 'FluxCalibrationMethod', 0, 'none', 'c'),
('XML_CALFLUXTABLE_ENTITIES', 'CalFluxTable', 'frequencyRanges', 'Frequency', 2, 'none', 'c'),
('XML_CALFLUXTABLE_ENTITIES', 'CalFluxTable', 'numFrequencyRanges', 'int', 0, 'none', 'c'),
('XML_CALFLUXTABLE_ENTITIES', 'CalFluxTable', 'numStokes', 'int', 0, 'none', 'c'),
('XML_CALFLUXTABLE_ENTITIES', 'CalFluxTable', 'PA', 'Angle', 2, 'none', 'd'),
('XML_CALFLUXTABLE_ENTITIES', 'CalFluxTable', 'PAError', 'Angle', 2, 'none', 'd'),
('XML_CALFLUXTABLE_ENTITIES', 'CalFluxTable', 'sizeError', 'Angle', 3, 'none', 'd'),
('XML_CALFLUXTABLE_ENTITIES', 'CalFluxTable', 'size', 'Angle', 3, 'none', 'd'),
('XML_CALFLUXTABLE_ENTITIES', 'CalFluxTable', 'sourceModel', 'SourceModel', 0, 'none', 'd'),
('XML_CALFLUXTABLE_ENTITIES', 'CalFluxTable', 'sourceName', 'String', 0, 'none', 'd'),
('XML_CALFLUXTABLE_ENTITIES', 'CalFluxTable', 'startValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALFLUXTABLE_ENTITIES', 'CalFluxTable', 'stokes', 'StokesParameter', 1, 'none', 'c'),
('XML_CALFOCUSMODELTABL_ENTITIES', 'CalFocusModelTable', 'antennaMake', 'AntennaMake', 0, 'none', 'c'),
('XML_CALFOCUSMODELTABL_ENTITIES', 'CalFocusModelTable', 'antennaName', 'String', 0, 'none', 'c'),
('XML_CALFOCUSMODELTABL_ENTITIES', 'CalFocusModelTable', 'calDataId', 'Tag', 0, 'b', 'c'),
('XML_CALFOCUSMODELTABL_ENTITIES', 'CalFocusModelTable', 'calReductionId', 'Tag', 0, 'b', 'c'),
('XML_CALFOCUSMODELTABL_ENTITIES', 'CalFocusModelTable', 'coeffError', 'float', 1, 'none', 'c'),
('XML_CALFOCUSMODELTABL_ENTITIES', 'CalFocusModelTable', 'coeffFixed', 'boolean', 1, 'none', 'c'),
('XML_CALFOCUSMODELTABL_ENTITIES', 'CalFocusModelTable', 'coeffFormula', 'String', 1, 'none', 'c'),
('XML_CALFOCUSMODELTABL_ENTITIES', 'CalFocusModelTable', 'coeffName', 'String', 1, 'none', 'c'),
('XML_CALFOCUSMODELTABL_ENTITIES', 'CalFocusModelTable', 'coeffValue', 'float', 1, 'none', 'c'),
('XML_CALFOCUSMODELTABL_ENTITIES', 'CalFocusModelTable', 'endValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALFOCUSMODELTABL_ENTITIES', 'CalFocusModelTable', 'focusModel', 'String', 0, 'none', 'c'),
('XML_CALFOCUSMODELTABL_ENTITIES', 'CalFocusModelTable', 'focusRMS', 'Length', 1, 'none', 'c'),
('XML_CALFOCUSMODELTABL_ENTITIES', 'CalFocusModelTable', 'numCoeff', 'int', 0, 'none', 'c'),
('XML_CALFOCUSMODELTABL_ENTITIES', 'CalFocusModelTable', 'numSourceObs', 'int', 0, 'none', 'c'),
('XML_CALFOCUSMODELTABL_ENTITIES', 'CalFocusModelTable', 'polarizationType', 'PolarizationType', 0, 'none', 'c'),
('XML_CALFOCUSMODELTABL_ENTITIES', 'CalFocusModelTable', 'receiverBand', 'ReceiverBand', 0, 'none', 'c'),
('XML_CALFOCUSMODELTABL_ENTITIES', 'CalFocusModelTable', 'reducedChiSquared', 'double', 0, 'none', 'c'),
('XML_CALFOCUSMODELTABL_ENTITIES', 'CalFocusModelTable', 'startValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'ambientTemperature', 'Temperature', 0, 'none', 'c'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'antennaName', 'String', 0, 'none', 'c'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'atmPhaseCorrection', 'AtmPhaseCorrection', 0, 'none', 'c'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'calDataId', 'Tag', 0, 'b', 'c'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'calReductionId', 'Tag', 0, 'b', 'c'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'endValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'focusCurveWasFixed', 'boolean', 1, 'none', 'd'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'focusCurveWidth', 'Length', 2, 'none', 'd'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'focusCurveWidthError', 'Length', 2, 'none', 'd'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'focusMethod', 'FocusMethod', 0, 'none', 'c'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'frequencyRange', 'Frequency', 1, 'none', 'c'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'numReceptor', 'int', 0, 'none', 'c'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'offIntensity', 'Temperature', 1, 'none', 'd'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'offIntensityError', 'Temperature', 1, 'none', 'd'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'offIntensityWasFixed', 'boolean', 0, 'none', 'd'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'offset', 'Length', 2, 'none', 'c'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'offsetError', 'Length', 2, 'none', 'c'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'offsetWasTied', 'boolean', 2, 'none', 'c'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'peakIntensity', 'Temperature', 1, 'none', 'd'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'peakIntensityError', 'Temperature', 1, 'none', 'd'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'peakIntensityWasFixed', 'boolean', 0, 'none', 'd'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'pointingDirection', 'Angle', 1, 'none', 'c'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'polarizationsAveraged', 'boolean', 0, 'none', 'd'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'polarizationTypes', 'PolarizationType', 1, 'none', 'c'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'position', 'Length', 2, 'none', 'c'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'receiverBand', 'ReceiverBand', 0, 'none', 'c'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'reducedChiSquared', 'double', 2, 'none', 'c'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'startValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALFOCUSTABLE_ENTITIES', 'CalFocusTable', 'wereFixed', 'boolean', 1, 'none', 'c'),
('XML_CALGAINTABLE_ENTITIES', 'CalGainTable', 'calDataId', 'Tag', 0, 'b', 'c'),
('XML_CALGAINTABLE_ENTITIES', 'CalGainTable', 'calReductionId', 'Tag', 0, 'b', 'c'),
('XML_CALGAINTABLE_ENTITIES', 'CalGainTable', 'endValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALGAINTABLE_ENTITIES', 'CalGainTable', 'fit', 'float', 0, 'none', 'c'),
('XML_CALGAINTABLE_ENTITIES', 'CalGainTable', 'fitWeight', 'float', 0, 'none', 'c'),
('XML_CALGAINTABLE_ENTITIES', 'CalGainTable', 'gain', 'float', 0, 'none', 'c'),
('XML_CALGAINTABLE_ENTITIES', 'CalGainTable', 'gainValid', 'boolean', 0, 'none', 'c'),
('XML_CALGAINTABLE_ENTITIES', 'CalGainTable', 'startValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALGAINTABLE_ENTITIES', 'CalGainTable', 'totalFit', 'float', 0, 'none', 'c'),
('XML_CALGAINTABLE_ENTITIES', 'CalGainTable', 'totalFitWeight', 'float', 0, 'none', 'c'),
('XML_CALGAINTABLE_ENTITIES', 'CalGainTable', 'totalGainValid', 'boolean', 0, 'none', 'c'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'ambientTemperature', 'Temperature', 0, 'none', 'c'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'antennaMake', 'AntennaMake', 0, 'none', 'c'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'antennaName', 'String', 0, 'none', 'c'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'beamMapUID', 'EntityRef', 0, 'none', 'c'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'calDataId', 'Tag', 0, 'b', 'c'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'calReductionId', 'Tag', 0, 'b', 'c'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'direction', 'Angle', 1, 'none', 'c'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'endValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'focusPosition', 'Length', 1, 'none', 'c'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'frequencyRange', 'Frequency', 1, 'none', 'c'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'gravCorrection', 'boolean', 0, 'none', 'd'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'gravOptRange', 'Angle', 1, 'none', 'd'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'illuminationTaper', 'double', 0, 'none', 'c'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'numPanelModes', 'int', 0, 'none', 'c'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'numReceptor', 'int', 0, 'none', 'c'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'numScrew', 'int', 0, 'none', 'd'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'polarizationTypes', 'PolarizationType', 0, 'none', 'c'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'rawRMS', 'Length', 0, 'none', 'c'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'receiverBand', 'ReceiverBand', 0, 'none', 'c'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'screwMotion', 'Length', 1, 'none', 'd'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'screwMotionError', 'Length', 1, 'none', 'd'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'screwName', 'String', 1, 'none', 'd'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'startValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'surfaceMapUID', 'EntityRef', 0, 'none', 'c'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'tempCorrection', 'boolean', 0, 'none', 'd'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'tempOptRange', 'Temperature', 1, 'none', 'd'),
('XML_CALHOLOGRAPHYTABL_ENTITIES', 'CalHolographyTable', 'weightedRMS', 'Length', 0, 'none', 'c'),
('XML_CALPHASETABLE_ENTITIES', 'CalPhaseTable', 'ampli', 'float', 2, 'none', 'c'),
('XML_CALPHASETABLE_ENTITIES', 'CalPhaseTable', 'antennaNames', 'String', 2, 'none', 'c'),
('XML_CALPHASETABLE_ENTITIES', 'CalPhaseTable', 'atmPhaseCorrection', 'AtmPhaseCorrection', 0, 'none', 'c'),
('XML_CALPHASETABLE_ENTITIES', 'CalPhaseTable', 'basebandName', 'BasebandName', 0, 'none', 'c'),
('XML_CALPHASETABLE_ENTITIES', 'CalPhaseTable', 'baselineLengths', 'Length', 1, 'none', 'c'),
('XML_CALPHASETABLE_ENTITIES', 'CalPhaseTable', 'calDataId', 'Tag', 0, 'b', 'c'),
('XML_CALPHASETABLE_ENTITIES', 'CalPhaseTable', 'calReductionId', 'Tag', 0, 'b', 'c'),
('XML_CALPHASETABLE_ENTITIES', 'CalPhaseTable', 'correctionValidity', 'boolean', 1, 'none', 'd'),
('XML_CALPHASETABLE_ENTITIES', 'CalPhaseTable', 'decorrelationFactor', 'float', 2, 'none', 'c'),
('XML_CALPHASETABLE_ENTITIES', 'CalPhaseTable', 'direction', 'Angle', 1, 'none', 'c'),
('XML_CALPHASETABLE_ENTITIES', 'CalPhaseTable', 'endValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALPHASETABLE_ENTITIES', 'CalPhaseTable', 'frequencyRange', 'Frequency', 1, 'none', 'c'),
('XML_CALPHASETABLE_ENTITIES', 'CalPhaseTable', 'integrationTime', 'Interval', 0, 'none', 'c'),
('XML_CALPHASETABLE_ENTITIES', 'CalPhaseTable', 'numBaseline', 'int', 0, 'none', 'c'),
('XML_CALPHASETABLE_ENTITIES', 'CalPhaseTable', 'numReceptor', 'int', 0, 'none', 'c'),
('XML_CALPHASETABLE_ENTITIES', 'CalPhaseTable', 'phase', 'float', 2, 'none', 'c'),
('XML_CALPHASETABLE_ENTITIES', 'CalPhaseTable', 'phaseRMS', 'float', 2, 'none', 'c'),
('XML_CALPHASETABLE_ENTITIES', 'CalPhaseTable', 'polarizationTypes', 'PolarizationType', 1, 'none', 'c'),
('XML_CALPHASETABLE_ENTITIES', 'CalPhaseTable', 'receiverBand', 'ReceiverBand', 0, 'none', 'c'),
('XML_CALPHASETABLE_ENTITIES', 'CalPhaseTable', 'startValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALPHASETABLE_ENTITIES', 'CalPhaseTable', 'statPhaseRMS', 'float', 2, 'none', 'c'),
('XML_CALPOINTINGMODELT_ENTITIES', 'CalPointingModelTable', 'antennaMake', 'AntennaMake', 0, 'none', 'c'),
('XML_CALPOINTINGMODELT_ENTITIES', 'CalPointingModelTable', 'antennaName', 'String', 0, 'none', 'c'),
('XML_CALPOINTINGMODELT_ENTITIES', 'CalPointingModelTable', 'azimuthRMS', 'Angle', 0, 'none', 'c'),
('XML_CALPOINTINGMODELT_ENTITIES', 'CalPointingModelTable', 'calDataId', 'Tag', 0, 'b', 'c'),
('XML_CALPOINTINGMODELT_ENTITIES', 'CalPointingModelTable', 'calReductionId', 'Tag', 0, 'b', 'c'),
('XML_CALPOINTINGMODELT_ENTITIES', 'CalPointingModelTable', 'coeffError', 'float', 1, 'none', 'c'),
('XML_CALPOINTINGMODELT_ENTITIES', 'CalPointingModelTable', 'coeffFixed', 'boolean', 1, 'none', 'c'),
('XML_CALPOINTINGMODELT_ENTITIES', 'CalPointingModelTable', 'coeffFormula', 'String', 1, 'none', 'd'),
('XML_CALPOINTINGMODELT_ENTITIES', 'CalPointingModelTable', 'coeffName', 'String', 1, 'none', 'c'),
('XML_CALPOINTINGMODELT_ENTITIES', 'CalPointingModelTable', 'coeffVal', 'float', 1, 'none', 'c'),
('XML_CALPOINTINGMODELT_ENTITIES', 'CalPointingModelTable', 'elevationRms', 'Angle', 0, 'none', 'c'),
('XML_CALPOINTINGMODELT_ENTITIES', 'CalPointingModelTable', 'endValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALPOINTINGMODELT_ENTITIES', 'CalPointingModelTable', 'numCoeff', 'int', 0, 'none', 'c'),
('XML_CALPOINTINGMODELT_ENTITIES', 'CalPointingModelTable', 'numObs', 'int', 0, 'none', 'd'),
('XML_CALPOINTINGMODELT_ENTITIES', 'CalPointingModelTable', 'pointingModelMode', 'PointingModelMode', 0, 'none', 'c'),
('XML_CALPOINTINGMODELT_ENTITIES', 'CalPointingModelTable', 'polarizationType', 'PolarizationType', 0, 'none', 'c'),
('XML_CALPOINTINGMODELT_ENTITIES', 'CalPointingModelTable', 'receiverBand', 'ReceiverBand', 0, 'none', 'c'),
('XML_CALPOINTINGMODELT_ENTITIES', 'CalPointingModelTable', 'reducedChiSquared', 'double', 0, 'none', 'c'),
('XML_CALPOINTINGMODELT_ENTITIES', 'CalPointingModelTable', 'skyRMS', 'Angle', 0, 'none', 'c'),
('XML_CALPOINTINGMODELT_ENTITIES', 'CalPointingModelTable', 'startValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'ambientTemperature', 'Temperature', 0, 'none', 'c'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'antennaMake', 'AntennaMake', 0, 'none', 'c'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'antennaName', 'String', 0, 'none', 'c'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'atmPhaseCorrection', 'AtmPhaseCorrection', 0, 'none', 'c'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'averagedPolarizations', 'boolean', 0, 'none', 'd'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'beamPA', 'Angle', 1, 'none', 'd'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'beamPAError', 'Angle', 1, 'none', 'd'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'beamPAWasFixed', 'boolean', 0, 'none', 'd'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'beamWidth', 'Angle', 2, 'none', 'd'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'beamWidthError', 'Angle', 2, 'none', 'd'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'beamWidthWasFixed', 'boolean', 1, 'none', 'd'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'calDataId', 'Tag', 0, 'b', 'c'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'calReductionId', 'Tag', 0, 'b', 'c'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'collError', 'Angle', 2, 'none', 'c'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'collOffsetAbsolute', 'Angle', 2, 'none', 'c'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'collOffsetRelative', 'Angle', 2, 'none', 'c'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'collOffsetTied', 'boolean', 2, 'none', 'c'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'direction', 'Angle', 1, 'none', 'c'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'endValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'frequencyRange', 'Frequency', 1, 'none', 'c'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'numReceptor', 'int', 0, 'none', 'c'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'offIntensity', 'Temperature', 1, 'none', 'd'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'offIntensityError', 'Temperature', 1, 'none', 'd'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'offIntensityWasFixed', 'boolean', 0, 'none', 'd'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'peakIntensity', 'Temperature', 1, 'none', 'd'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'peakIntensityError', 'Temperature', 1, 'none', 'd'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'peakIntensityWasFixed', 'boolean', 0, 'none', 'd'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'pointingMethod', 'PointingMethod', 0, 'none', 'c'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'pointingModelMode', 'PointingModelMode', 0, 'none', 'c'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'polarizationTypes', 'PolarizationType', 1, 'none', 'c'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'receiverBand', 'ReceiverBand', 0, 'none', 'c'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'reducedChiSquared', 'double', 1, 'none', 'c'),
('XML_CALPOINTINGTABLE_ENTITIES', 'CalPointingTable', 'startValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALPOSITIONTABLE_ENTITIES', 'CalPositionTable', 'antennaName', 'String', 0, 'none', 'c'),
('XML_CALPOSITIONTABLE_ENTITIES', 'CalPositionTable', 'antennaPosition', 'Length', 1, 'none', 'c'),
('XML_CALPOSITIONTABLE_ENTITIES', 'CalPositionTable', 'atmPhaseCorrection', 'AtmPhaseCorrection', 0, 'none', 'c'),
('XML_CALPOSITIONTABLE_ENTITIES', 'CalPositionTable', 'axesOffset', 'Length', 0, 'none', 'c'),
('XML_CALPOSITIONTABLE_ENTITIES', 'CalPositionTable', 'axesOffsetErr', 'Length', 0, 'none', 'c'),
('XML_CALPOSITIONTABLE_ENTITIES', 'CalPositionTable', 'axesOffsetFixed', 'boolean', 0, 'none', 'c'),
('XML_CALPOSITIONTABLE_ENTITIES', 'CalPositionTable', 'calDataId', 'Tag', 0, 'b', 'c'),
('XML_CALPOSITIONTABLE_ENTITIES', 'CalPositionTable', 'calReductionId', 'Tag', 0, 'b', 'c'),
('XML_CALPOSITIONTABLE_ENTITIES', 'CalPositionTable', 'delayRms', 'double', 0, 'none', 'd'),
('XML_CALPOSITIONTABLE_ENTITIES', 'CalPositionTable', 'endValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALPOSITIONTABLE_ENTITIES', 'CalPositionTable', 'numAntenna', 'int', 0, 'none', 'c'),
('XML_CALPOSITIONTABLE_ENTITIES', 'CalPositionTable', 'phaseRms', 'Angle', 0, 'none', 'd'),
('XML_CALPOSITIONTABLE_ENTITIES', 'CalPositionTable', 'positionErr', 'Length', 1, 'none', 'c'),
('XML_CALPOSITIONTABLE_ENTITIES', 'CalPositionTable', 'positionMethod', 'PositionMethod', 0, 'none', 'c'),
('XML_CALPOSITIONTABLE_ENTITIES', 'CalPositionTable', 'positionOffset', 'Length', 1, 'none', 'c'),
('XML_CALPOSITIONTABLE_ENTITIES', 'CalPositionTable', 'receiverBand', 'ReceiverBand', 0, 'none', 'c'),
('XML_CALPOSITIONTABLE_ENTITIES', 'CalPositionTable', 'reducedChiSquared', 'double', 0, 'none', 'c'),
('XML_CALPOSITIONTABLE_ENTITIES', 'CalPositionTable', 'refAntennaNames', 'String', 1, 'none', 'c'),
('XML_CALPOSITIONTABLE_ENTITIES', 'CalPositionTable', 'startValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALPOSITIONTABLE_ENTITIES', 'CalPositionTable', 'stationName', 'String', 0, 'none', 'c'),
('XML_CALPOSITIONTABLE_ENTITIES', 'CalPositionTable', 'stationPosition', 'Length', 1, 'none', 'c'),
('XML_CALPRIMARYBEAMTAB_ENTITIES', 'CalPrimaryBeamTable', 'antennaMake', 'AntennaMake', 0, 'none', 'c'),
('XML_CALPRIMARYBEAMTAB_ENTITIES', 'CalPrimaryBeamTable', 'antennaName', 'String', 0, 'none', 'c'),
('XML_CALPRIMARYBEAMTAB_ENTITIES', 'CalPrimaryBeamTable', 'beamDescriptionUID', 'EntityRef', 0, 'none', 'c'),
('XML_CALPRIMARYBEAMTAB_ENTITIES', 'CalPrimaryBeamTable', 'calDataId', 'Tag', 0, 'b', 'c'),
('XML_CALPRIMARYBEAMTAB_ENTITIES', 'CalPrimaryBeamTable', 'calReductionId', 'Tag', 0, 'b', 'c'),
('XML_CALPRIMARYBEAMTAB_ENTITIES', 'CalPrimaryBeamTable', 'descriptionType', 'PrimaryBeamDescription', 0, 'none', 'c'),
('XML_CALPRIMARYBEAMTAB_ENTITIES', 'CalPrimaryBeamTable', 'direction', 'Angle', 1, 'none', 'c'),
('XML_CALPRIMARYBEAMTAB_ENTITIES', 'CalPrimaryBeamTable', 'endValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALPRIMARYBEAMTAB_ENTITIES', 'CalPrimaryBeamTable', 'frequencyRange', 'Frequency', 1, 'none', 'c'),
('XML_CALPRIMARYBEAMTAB_ENTITIES', 'CalPrimaryBeamTable', 'imageChannelNumber', 'int', 1, 'none', 'c'),
('XML_CALPRIMARYBEAMTAB_ENTITIES', 'CalPrimaryBeamTable', 'imageNominalFrequency', 'Frequency', 1, 'none', 'c'),
('XML_CALPRIMARYBEAMTAB_ENTITIES', 'CalPrimaryBeamTable', 'mainBeamEfficiency', 'double', 1, 'none', 'c'),
('XML_CALPRIMARYBEAMTAB_ENTITIES', 'CalPrimaryBeamTable', 'maxValidDirection', 'Angle', 1, 'none', 'c'),
('XML_CALPRIMARYBEAMTAB_ENTITIES', 'CalPrimaryBeamTable', 'minValidDirection', 'Angle', 1, 'none', 'c'),
('XML_CALPRIMARYBEAMTAB_ENTITIES', 'CalPrimaryBeamTable', 'numReceptor', 'int', 0, 'none', 'c'),
('XML_CALPRIMARYBEAMTAB_ENTITIES', 'CalPrimaryBeamTable', 'numSubband', 'int', 0, 'none', 'c'),
('XML_CALPRIMARYBEAMTAB_ENTITIES', 'CalPrimaryBeamTable', 'polarizationTypes', 'PolarizationType', 0, 'none', 'c'),
('XML_CALPRIMARYBEAMTAB_ENTITIES', 'CalPrimaryBeamTable', 'receiverBand', 'ReceiverBand', 0, 'none', 'c'),
('XML_CALPRIMARYBEAMTAB_ENTITIES', 'CalPrimaryBeamTable', 'relativeAmplitudeRms', 'float', 0, 'none', 'c'),
('XML_CALPRIMARYBEAMTAB_ENTITIES', 'CalPrimaryBeamTable', 'startValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALREDUCTIONTABLE_ENTITIES', 'CalReductionTable', 'appliedCalibrations', 'String', 1, 'none', 'c'),
('XML_CALREDUCTIONTABLE_ENTITIES', 'CalReductionTable', 'calReductionId', 'Tag', 0, 'a', 'c'),
('XML_CALREDUCTIONTABLE_ENTITIES', 'CalReductionTable', 'invalidConditions', 'InvalidatingCondition', 0, 'none', 'c'),
('XML_CALREDUCTIONTABLE_ENTITIES', 'CalReductionTable', 'messages', 'String', 0, 'none', 'c'),
('XML_CALREDUCTIONTABLE_ENTITIES', 'CalReductionTable', 'numApplied', 'int', 0, 'none', 'c'),
('XML_CALREDUCTIONTABLE_ENTITIES', 'CalReductionTable', 'numInvalidConditions', 'int', 0, 'none', 'c'),
('XML_CALREDUCTIONTABLE_ENTITIES', 'CalReductionTable', 'numParam', 'int', 0, 'none', 'c'),
('XML_CALREDUCTIONTABLE_ENTITIES', 'CalReductionTable', 'paramSet', 'String', 1, 'none', 'c'),
('XML_CALREDUCTIONTABLE_ENTITIES', 'CalReductionTable', 'software', 'String', 0, 'none', 'c'),
('XML_CALREDUCTIONTABLE_ENTITIES', 'CalReductionTable', 'softwareVersion', 'String', 0, 'none', 'c'),
('XML_CALREDUCTIONTABLE_ENTITIES', 'CalReductionTable', 'timeReduced', 'ArrayTime', 0, 'none', 'c'),
('XML_CALSEEINGTABLE_ENTITIES', 'CalSeeingTable', 'atmPhaseCorrection', 'AtmPhaseCorrection', 0, 'none', 'c'),
('XML_CALSEEINGTABLE_ENTITIES', 'CalSeeingTable', 'baselineLengths', 'Length', 1, 'none', 'c'),
('XML_CALSEEINGTABLE_ENTITIES', 'CalSeeingTable', 'calDataId', 'Tag', 0, 'b', 'c'),
('XML_CALSEEINGTABLE_ENTITIES', 'CalSeeingTable', 'calReductionId', 'Tag', 0, 'b', 'c'),
('XML_CALSEEINGTABLE_ENTITIES', 'CalSeeingTable', 'endValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALSEEINGTABLE_ENTITIES', 'CalSeeingTable', 'exponent', 'float', 0, 'none', 'd'),
('XML_CALSEEINGTABLE_ENTITIES', 'CalSeeingTable', 'frequencyRange', 'Frequency', 1, 'none', 'c'),
('XML_CALSEEINGTABLE_ENTITIES', 'CalSeeingTable', 'integrationTime', 'Interval', 0, 'none', 'c'),
('XML_CALSEEINGTABLE_ENTITIES', 'CalSeeingTable', 'numBaseLengths', 'int', 0, 'none', 'c'),
('XML_CALSEEINGTABLE_ENTITIES', 'CalSeeingTable', 'outerScale', 'Length', 0, 'none', 'd'),
('XML_CALSEEINGTABLE_ENTITIES', 'CalSeeingTable', 'outerScaleRMS', 'Angle', 0, 'none', 'd'),
('XML_CALSEEINGTABLE_ENTITIES', 'CalSeeingTable', 'phaseRMS', 'Angle', 1, 'none', 'c'),
('XML_CALSEEINGTABLE_ENTITIES', 'CalSeeingTable', 'seeing', 'Angle', 0, 'none', 'c'),
('XML_CALSEEINGTABLE_ENTITIES', 'CalSeeingTable', 'seeingError', 'Angle', 0, 'none', 'c'),
('XML_CALSEEINGTABLE_ENTITIES', 'CalSeeingTable', 'startValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALWVRTABLE_ENTITIES', 'CalWVRTable', 'antennaName', 'String', 0, 'none', 'c'),
('XML_CALWVRTABLE_ENTITIES', 'CalWVRTable', 'calDataId', 'Tag', 0, 'b', 'c'),
('XML_CALWVRTABLE_ENTITIES', 'CalWVRTable', 'calReductionId', 'Tag', 0, 'b', 'c'),
('XML_CALWVRTABLE_ENTITIES', 'CalWVRTable', 'chanFreq', 'Frequency', 1, 'none', 'c'),
('XML_CALWVRTABLE_ENTITIES', 'CalWVRTable', 'chanWidth', 'Frequency', 1, 'none', 'c'),
('XML_CALWVRTABLE_ENTITIES', 'CalWVRTable', 'dryPath', 'float', 1, 'none', 'c'),
('XML_CALWVRTABLE_ENTITIES', 'CalWVRTable', 'endValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALWVRTABLE_ENTITIES', 'CalWVRTable', 'inputAntennaNames', 'String', 1, 'none', 'c'),
('XML_CALWVRTABLE_ENTITIES', 'CalWVRTable', 'numChan', 'int', 0, 'none', 'c'),
('XML_CALWVRTABLE_ENTITIES', 'CalWVRTable', 'numInputAntennas', 'int', 0, 'none', 'c'),
('XML_CALWVRTABLE_ENTITIES', 'CalWVRTable', 'numPoly', 'int', 0, 'none', 'c'),
('XML_CALWVRTABLE_ENTITIES', 'CalWVRTable', 'pathCoeff', 'float', 3, 'none', 'c'),
('XML_CALWVRTABLE_ENTITIES', 'CalWVRTable', 'polyFreqLimits', 'Frequency', 1, 'none', 'c'),
('XML_CALWVRTABLE_ENTITIES', 'CalWVRTable', 'refTemp', 'Temperature', 2, 'none', 'c'),
('XML_CALWVRTABLE_ENTITIES', 'CalWVRTable', 'startValidTime', 'ArrayTime', 0, 'none', 'c'),
('XML_CALWVRTABLE_ENTITIES', 'CalWVRTable', 'water', 'Length', 0, 'none', 'c'),
('XML_CALWVRTABLE_ENTITIES', 'CalWVRTable', 'wetPath', 'float', 1, 'none', 'c'),
('XML_CALWVRTABLE_ENTITIES', 'CalWVRTable', 'wvrMethod', 'WVRMethod', 0, 'none', 'c'),
('XML_CONFIGDESCRIPTION_ENTITIES', 'ConfigDescriptionTable', 'antennaId', 'Tag', 1, 'b', 'c'),
('XML_CONFIGDESCRIPTION_ENTITIES', 'ConfigDescriptionTable', 'assocConfigDescriptionId', 'Tag', 1, 'b', 'd'),
('XML_CONFIGDESCRIPTION_ENTITIES', 'ConfigDescriptionTable', 'assocNature', 'SpectralResolutionType', 1, 'none', 'd'),
('XML_CONFIGDESCRIPTION_ENTITIES', 'ConfigDescriptionTable', 'atmPhaseCorrection', 'AtmPhaseCorrection', 1, 'none', 'c'),
('XML_CONFIGDESCRIPTION_ENTITIES', 'ConfigDescriptionTable', 'configDescriptionId', 'Tag', 0, 'a', 'c'),
('XML_CONFIGDESCRIPTION_ENTITIES', 'ConfigDescriptionTable', 'correlationMode', 'CorrelationMode', 0, 'none', 'c'),
('XML_CONFIGDESCRIPTION_ENTITIES', 'ConfigDescriptionTable', 'dataDescriptionId', 'Tag', 1, 'b', 'c'),
('XML_CONFIGDESCRIPTION_ENTITIES', 'ConfigDescriptionTable', 'feedId', 'int', 1, 'b', 'c'),
('XML_CONFIGDESCRIPTION_ENTITIES', 'ConfigDescriptionTable', 'numAntenna', 'int', 0, 'none', 'c'),
('XML_CONFIGDESCRIPTION_ENTITIES', 'ConfigDescriptionTable', 'numAssocValues', 'int', 0, 'none', 'd'),
('XML_CONFIGDESCRIPTION_ENTITIES', 'ConfigDescriptionTable', 'numAtmPhaseCorrection', 'int', 0, 'none', 'c'),
('XML_CONFIGDESCRIPTION_ENTITIES', 'ConfigDescriptionTable', 'numDataDescription', 'int', 0, 'none', 'c'),
('XML_CONFIGDESCRIPTION_ENTITIES', 'ConfigDescriptionTable', 'numFeed', 'int', 0, 'none', 'c'),
('XML_CONFIGDESCRIPTION_ENTITIES', 'ConfigDescriptionTable', 'phasedArrayList', 'int', 1, 'none', 'd'),
('XML_CONFIGDESCRIPTION_ENTITIES', 'ConfigDescriptionTable', 'processorId', 'Tag', 0, 'b', 'c'),
('XML_CONFIGDESCRIPTION_ENTITIES', 'ConfigDescriptionTable', 'processorType', 'ProcessorType', 0, 'none', 'c'),
('XML_CONFIGDESCRIPTION_ENTITIES', 'ConfigDescriptionTable', 'spectralType', 'SpectralResolutionType', 0, 'none', 'c'),
('XML_CONFIGDESCRIPTION_ENTITIES', 'ConfigDescriptionTable', 'switchCycleId', 'Tag', 1, 'b', 'c'),
('XML_CORRELATORMODETAB_ENTITIES', 'CorrelatorModeTable', 'accumMode', 'AccumMode', 0, 'none', 'c'),
('XML_CORRELATORMODETAB_ENTITIES', 'CorrelatorModeTable', 'axesOrderArray', 'AxisName', 1, 'none', 'c'),
('XML_CORRELATORMODETAB_ENTITIES', 'CorrelatorModeTable', 'basebandConfig', 'int', 1, 'none', 'c'),
('XML_CORRELATORMODETAB_ENTITIES', 'CorrelatorModeTable', 'basebandNames', 'BasebandName', 1, 'none', 'c'),
('XML_CORRELATORMODETAB_ENTITIES', 'CorrelatorModeTable', 'binMode', 'int', 0, 'none', 'c'),
('XML_CORRELATORMODETAB_ENTITIES', 'CorrelatorModeTable', 'correlatorModeId', 'Tag', 0, 'a', 'c'),
('XML_CORRELATORMODETAB_ENTITIES', 'CorrelatorModeTable', 'correlatorName', 'CorrelatorName', 0, 'none', 'c'),
('XML_CORRELATORMODETAB_ENTITIES', 'CorrelatorModeTable', 'filterMode', 'FilterMode', 1, 'none', 'c'),
('XML_CORRELATORMODETAB_ENTITIES', 'CorrelatorModeTable', 'numAxes', 'int', 0, 'none', 'c'),
('XML_CORRELATORMODETAB_ENTITIES', 'CorrelatorModeTable', 'numBaseband', 'int', 0, 'none', 'c'),
('XML_DATADESCRIPTIONTA_ENTITIES', 'DataDescriptionTable', 'dataDescriptionId', 'Tag', 0, 'a', 'c'),
('XML_DATADESCRIPTIONTA_ENTITIES', 'DataDescriptionTable', 'polOrHoloId', 'Tag', 0, 'b', 'c'),
('XML_DATADESCRIPTIONTA_ENTITIES', 'DataDescriptionTable', 'spectralWindowId', 'Tag', 0, 'b', 'c'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'antennaDelay', 'double', 0, 'none', 'd'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'antennaId', 'Tag', 0, 'b', 'c'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'atmosphericDryDelay', 'double', 1, 'none', 'c'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'atmosphericGroupDelay', 'double', 0, 'none', 'd'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'atmosphericGroupDelayRate', 'double', 0, 'none', 'd'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'atmosphericWetDelay', 'double', 1, 'none', 'c'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'crossPolarizationDelay', 'double', 0, 'none', 'd'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'dispersiveDelay', 'double', 1, 'none', 'd'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'dispersiveDelayRate', 'double', 0, 'none', 'd'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'electronicDelay', 'double', 1, 'none', 'd'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'electronicDelayRate', 'double', 1, 'none', 'd'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'fieldId', 'Tag', 0, 'none', 'c'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'geometricDelay', 'double', 1, 'none', 'c'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'geometricDelayRate', 'double', 0, 'none', 'd'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'groupDelay', 'double', 1, 'none', 'd'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'groupDelayRate', 'double', 1, 'none', 'c'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'IFDelay', 'double', 1, 'none', 'd'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'LODelay', 'double', 1, 'none', 'd'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'LOOffset', 'Frequency', 1, 'none', 'd'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'LOOffsetRate', 'Frequency', 1, 'none', 'd'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'numLO', 'int', 0, 'none', 'd'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'numPoly', 'int', 0, 'none', 'c'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'numReceptor', 'int', 0, 'none', 'd'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'padDelay', 'double', 0, 'none', 'd'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'phaseDelay', 'double', 1, 'none', 'd'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'phaseDelayRate', 'double', 1, 'none', 'c'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'polarizationType', 'PolarizationType', 1, 'none', 'd'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'receiverDelay', 'double', 1, 'none', 'd'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'spectralWindowId', 'Tag', 0, 'b', 'c'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'timeInterval', 'ArrayTimeInterval', 0, 'none', 'c'),
('XML_DELAYMODELTABLE_ENTITIES', 'DelayModelTable', 'timeOrigin', 'ArrayTime', 0, 'none', 'c'),
('XML_DOPPLERTABLE_ENTITIES', 'DopplerTable', 'dopplerId', 'int', 0, 'a', 'c'),
('XML_DOPPLERTABLE_ENTITIES', 'DopplerTable', 'sourceId', 'int', 0, 'b', 'c'),
('XML_DOPPLERTABLE_ENTITIES', 'DopplerTable', 'transitionIndex', 'int', 0, 'none', 'c'),
('XML_DOPPLERTABLE_ENTITIES', 'DopplerTable', 'velDef', 'DopplerReferenceCode', 0, 'none', 'c'),
('XML_EPHEMERISTABLE_ENTITIES', 'EphemerisTable', 'ephemerisId', 'Tag', 0, 'a', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'aborted', 'boolean', 0, 'none', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'antennaId', 'Tag', 1, 'b', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'basePa', 'Angle', 0, 'none', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'baseRangeMax', 'Length', 0, 'none', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'baseRangeMin', 'Length', 0, 'none', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'baseRmsMajor', 'Length', 0, 'none', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'baseRmsMinor', 'Length', 0, 'none', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'configName', 'String', 0, 'none', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'endTime', 'ArrayTime', 0, 'none', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'execBlockId', 'Tag', 0, 'a', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'execBlockNum', 'int', 0, 'none', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'execBlockUID', 'EntityRef', 0, 'none', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'numAntenna', 'int', 0, 'none', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'numObservingLog', 'int', 0, 'none', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'observerName', 'String', 0, 'none', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'observingLog', 'String', 0, 'none', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'observingScript', 'String', 0, 'none', 'd'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'observingScriptUID', 'EntityRef', 0, 'none', 'd'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'projectUID', 'EntityRef', 0, 'b', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'releaseDate', 'ArrayTime', 0, 'none', 'd'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'sBSummaryId', 'Tag', 0, 'b', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'scaleId', 'Tag', 0, 'none', 'd'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'schedulerMode', 'String', 0, 'none', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'sessionReference', 'EntityRef', 0, 'none', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'siteAltitude', 'Length', 0, 'none', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'siteLatitude', 'Angle', 0, 'none', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'siteLongitude', 'Angle', 0, 'none', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'startTime', 'ArrayTime', 0, 'none', 'c'),
('XML_EXECBLOCKTABLE_ENTITIES', 'ExecBlockTable', 'telescopeName', 'String', 0, 'none', 'c'),
('XML_FEEDTABLE_ENTITIES', 'FeedTable', 'antennaId', 'Tag', 0, 'b', 'c'),
('XML_FEEDTABLE_ENTITIES', 'FeedTable', 'beamOffset', 'double', 2, 'none', 'c'),
('XML_FEEDTABLE_ENTITIES', 'FeedTable', 'feedId', 'int', 0, 'a', 'c'),
('XML_FEEDTABLE_ENTITIES', 'FeedTable', 'feedNum', 'int', 0, 'none', 'd'),
('XML_FEEDTABLE_ENTITIES', 'FeedTable', 'focusReference', 'Length', 2, 'none', 'c'),
('XML_FEEDTABLE_ENTITIES', 'FeedTable', 'illumOffset', 'Length', 1, 'none', 'd'),
('XML_FEEDTABLE_ENTITIES', 'FeedTable', 'numReceptor', 'int', 0, 'none', 'c'),
('XML_FEEDTABLE_ENTITIES', 'FeedTable', 'polarizationTypes', 'PolarizationType', 0, 'none', 'c'),
('XML_FEEDTABLE_ENTITIES', 'FeedTable', 'polResponse', 'Complex', 0, 'none', 'c'),
('XML_FEEDTABLE_ENTITIES', 'FeedTable', 'position', 'Length', 1, 'none', 'd'),
('XML_FEEDTABLE_ENTITIES', 'FeedTable', 'receiverId', 'int', 1, 'b', 'c'),
('XML_FEEDTABLE_ENTITIES', 'FeedTable', 'receptorAngle', 'Angle', 1, 'none', 'c'),
('XML_FEEDTABLE_ENTITIES', 'FeedTable', 'spectralWindowId', 'Tag', 0, 'b', 'c'),
('XML_FEEDTABLE_ENTITIES', 'FeedTable', 'timeInterval', 'ArrayTimeInterval', 0, 'none', 'c'),
('XML_FIELDTABLE_ENTITIES', 'FieldTable', 'assocFieldId', 'Tag', 0, 'b', 'd'),
('XML_FIELDTABLE_ENTITIES', 'FieldTable', 'assocNature', 'String', 0, 'none', 'd'),
('XML_FIELDTABLE_ENTITIES', 'FieldTable', 'code', 'String', 0, 'none', 'c'),
('XML_FIELDTABLE_ENTITIES', 'FieldTable', 'delayDir', 'Angle', 2, 'none', 'c'),
('XML_FIELDTABLE_ENTITIES', 'FieldTable', 'directionCode', 'DirectionReferenceCode', 0, 'none', 'd'),
('XML_FIELDTABLE_ENTITIES', 'FieldTable', 'directionEquinox', 'ArrayTime', 0, 'none', 'd'),
('XML_FIELDTABLE_ENTITIES', 'FieldTable', 'ephemerisId', 'Tag', 0, 'b', 'd'),
('XML_FIELDTABLE_ENTITIES', 'FieldTable', 'fieldId', 'Tag', 0, 'a', 'c'),
('XML_FIELDTABLE_ENTITIES', 'FieldTable', 'fieldName', 'String', 0, 'none', 'd'),
('XML_FIELDTABLE_ENTITIES', 'FieldTable', 'numPoly', 'int', 0, 'none', 'c'),
('XML_FIELDTABLE_ENTITIES', 'FieldTable', 'phaseDir', 'Angle', 2, 'none', 'c'),
('XML_FIELDTABLE_ENTITIES', 'FieldTable', 'referenceDir', 'Angle', 2, 'none', 'c'),
('XML_FIELDTABLE_ENTITIES', 'FieldTable', 'sourceId', 'int', 0, 'b', 'd'),
('XML_FIELDTABLE_ENTITIES', 'FieldTable', 'time', 'ArrayTime', 0, 'none', 'd'),
('XML_FLAGCMDTABLE_ENTITIES', 'FlagCmdTable', 'applied', 'boolean', 0, 'none', 'c'),
('XML_FLAGCMDTABLE_ENTITIES', 'FlagCmdTable', 'command', 'String', 0, 'none', 'c'),
('XML_FLAGCMDTABLE_ENTITIES', 'FlagCmdTable', 'level', 'int', 0, 'none', 'c'),
('XML_FLAGCMDTABLE_ENTITIES', 'FlagCmdTable', 'reason', 'String', 0, 'none', 'c'),
('XML_FLAGCMDTABLE_ENTITIES', 'FlagCmdTable', 'severity', 'int', 0, 'none', 'c'),
('XML_FLAGCMDTABLE_ENTITIES', 'FlagCmdTable', 'timeInterval', 'ArrayTimeInterval', 0, 'none', 'c'),
('XML_FLAGCMDTABLE_ENTITIES', 'FlagCmdTable', 'type', 'String', 0, 'none', 'c'),
('XML_FLAGTABLE_ENTITIES', 'FlagTable', 'antennaId', 'Tag', 1, 'none', 'c'),
('XML_FLAGTABLE_ENTITIES', 'FlagTable', 'endTime', 'ArrayTime', 0, 'none', 'c'),
('XML_FLAGTABLE_ENTITIES', 'FlagTable', 'flagId', 'Tag', 0, 'a', 'c'),
('XML_FLAGTABLE_ENTITIES', 'FlagTable', 'numAntenna', 'int', 0, 'none', 'c'),
('XML_FLAGTABLE_ENTITIES', 'FlagTable', 'numPairedAntenna', 'int', 0, 'none', 'd'),
('XML_FLAGTABLE_ENTITIES', 'FlagTable', 'numPolarizationType', 'int', 0, 'none', 'd'),
('XML_FLAGTABLE_ENTITIES', 'FlagTable', 'numSpectralWindow', 'int', 0, 'none', 'd'),
('XML_FLAGTABLE_ENTITIES', 'FlagTable', 'pairedAntennaId', 'Tag', 1, 'none', 'd'),
('XML_FLAGTABLE_ENTITIES', 'FlagTable', 'polarizationType', 'PolarizationType', 1, 'none', 'd'),
('XML_FLAGTABLE_ENTITIES', 'FlagTable', 'reason', 'String', 0, 'none', 'c'),
('XML_FLAGTABLE_ENTITIES', 'FlagTable', 'spectralWindowId', 'Tag', 1, 'none', 'd'),
('XML_FLAGTABLE_ENTITIES', 'FlagTable', 'startTime', 'ArrayTime', 0, 'none', 'c'),
('XML_FOCUSMODELTABLE_ENTITIES', 'FocusModelTable', 'antennaId', 'Tag', 0, 'b', 'c'),
('XML_FOCUSMODELTABLE_ENTITIES', 'FocusModelTable', 'assocFocusModelId', 'int', 0, 'b', 'c'),
('XML_FOCUSMODELTABLE_ENTITIES', 'FocusModelTable', 'assocNature', 'String', 0, 'none', 'c'),
('XML_FOCUSMODELTABLE_ENTITIES', 'FocusModelTable', 'coeffFormula', 'String', 1, 'none', 'c'),
('XML_FOCUSMODELTABLE_ENTITIES', 'FocusModelTable', 'coeffName', 'String', 1, 'none', 'c'),
('XML_FOCUSMODELTABLE_ENTITIES', 'FocusModelTable', 'coeffVal', 'float', 1, 'none', 'c'),
('XML_FOCUSMODELTABLE_ENTITIES', 'FocusModelTable', 'focusModelId', 'int', 0, 'a', 'c'),
('XML_FOCUSMODELTABLE_ENTITIES', 'FocusModelTable', 'numCoeff', 'int', 0, 'none', 'c'),
('XML_FOCUSMODELTABLE_ENTITIES', 'FocusModelTable', 'polarizationType', 'PolarizationType', 0, 'none', 'c'),
('XML_FOCUSMODELTABLE_ENTITIES', 'FocusModelTable', 'receiverBand', 'ReceiverBand', 0, 'none', 'c'),
('XML_FOCUSTABLE_ENTITIES', 'FocusTable', 'antennaId', 'Tag', 0, 'b', 'c'),
('XML_FOCUSTABLE_ENTITIES', 'FocusTable', 'focusModelId', 'int', 0, 'b', 'c'),
('XML_FOCUSTABLE_ENTITIES', 'FocusTable', 'focusOffset', 'Length', 1, 'none', 'c'),
('XML_FOCUSTABLE_ENTITIES', 'FocusTable', 'focusRotationOffset', 'Angle', 1, 'none', 'c'),
('XML_FOCUSTABLE_ENTITIES', 'FocusTable', 'focusTracking', 'boolean', 0, 'none', 'c'),
('XML_FOCUSTABLE_ENTITIES', 'FocusTable', 'measuredFocusPosition', 'Length', 1, 'none', 'd'),
('XML_FOCUSTABLE_ENTITIES', 'FocusTable', 'measuredFocusRotation', 'Angle', 1, 'none', 'd'),
('XML_FOCUSTABLE_ENTITIES', 'FocusTable', 'timeInterval', 'ArrayTimeInterval', 0, 'none', 'c'),
('XML_FREQOFFSETTABLE_ENTITIES', 'FreqOffsetTable', 'antennaId', 'Tag', 0, 'b', 'c'),
('XML_FREQOFFSETTABLE_ENTITIES', 'FreqOffsetTable', 'feedId', 'int', 0, 'b', 'c'),
('XML_FREQOFFSETTABLE_ENTITIES', 'FreqOffsetTable', 'offset', 'Frequency', 0, 'none', 'c'),
('XML_FREQOFFSETTABLE_ENTITIES', 'FreqOffsetTable', 'spectralWindowId', 'Tag', 0, 'b', 'c'),
('XML_FREQOFFSETTABLE_ENTITIES', 'FreqOffsetTable', 'timeInterval', 'ArrayTimeInterval', 0, 'none', 'c'),
('XML_GAINTRACKINGTABLE_ENTITIES', 'GainTrackingTable', 'antennaId', 'Tag', 0, 'b', 'c'),
('XML_GAINTRACKINGTABLE_ENTITIES', 'GainTrackingTable', 'attenuator', 'float', 0, 'none', 'c'),
('XML_GAINTRACKINGTABLE_ENTITIES', 'GainTrackingTable', 'attFreq', 'double', 1, 'none', 'd'),
('XML_GAINTRACKINGTABLE_ENTITIES', 'GainTrackingTable', 'attSpectrum', 'Complex', 1, 'none', 'd'),
('XML_GAINTRACKINGTABLE_ENTITIES', 'GainTrackingTable', 'feedId', 'int', 0, 'b', 'c'),
('XML_GAINTRACKINGTABLE_ENTITIES', 'GainTrackingTable', 'numAttFreq', 'int', 0, 'none', 'd'),
('XML_GAINTRACKINGTABLE_ENTITIES', 'GainTrackingTable', 'numReceptor', 'int', 0, 'none', 'c'),
('XML_GAINTRACKINGTABLE_ENTITIES', 'GainTrackingTable', 'polarizationType', 'PolarizationType', 0, 'none', 'c'),
('XML_GAINTRACKINGTABLE_ENTITIES', 'GainTrackingTable', 'samplingLevel', 'float', 0, 'none', 'd'),
('XML_GAINTRACKINGTABLE_ENTITIES', 'GainTrackingTable', 'spectralWindowId', 'Tag', 0, 'b', 'c'),
('XML_GAINTRACKINGTABLE_ENTITIES', 'GainTrackingTable', 'timeInterval', 'ArrayTimeInterval', 0, 'none', 'c'),
('XML_HISTORYTABLE_ENTITIES', 'HistoryTable', 'application', 'String', 0, 'none', 'c'),
('XML_HISTORYTABLE_ENTITIES', 'HistoryTable', 'appParms', 'String', 0, 'none', 'c'),
('XML_HISTORYTABLE_ENTITIES', 'HistoryTable', 'cliCommand', 'String', 0, 'none', 'c'),
('XML_HISTORYTABLE_ENTITIES', 'HistoryTable', 'execBlockId', 'Tag', 0, 'b', 'c'),
('XML_HISTORYTABLE_ENTITIES', 'HistoryTable', 'message', 'String', 0, 'none', 'c'),
('XML_HISTORYTABLE_ENTITIES', 'HistoryTable', 'objectId', 'String', 0, 'b', 'c'),
('XML_HISTORYTABLE_ENTITIES', 'HistoryTable', 'origin', 'String', 0, 'none', 'c'),
('XML_HISTORYTABLE_ENTITIES', 'HistoryTable', 'priority', 'String', 0, 'none', 'c'),
('XML_HISTORYTABLE_ENTITIES', 'HistoryTable', 'time', 'ArrayTime', 0, 'none', 'c'),
('XML_HOLOGRAPHYTABLE_ENTITIES', 'HolographyTable', 'distance', 'Length', 0, 'none', 'c'),
('XML_HOLOGRAPHYTABLE_ENTITIES', 'HolographyTable', 'focus', 'Length', 0, 'none', 'c'),
('XML_HOLOGRAPHYTABLE_ENTITIES', 'HolographyTable', 'holographyId', 'Tag', 0, 'a', 'c'),
('XML_HOLOGRAPHYTABLE_ENTITIES', 'HolographyTable', 'numCorr', 'int', 0, 'none', 'c'),
('XML_HOLOGRAPHYTABLE_ENTITIES', 'HolographyTable', 'type', 'HolographyChannelType', 1, 'none', 'c'),
('XML_MAINTABLE_ENTITIES', 'MainTable', 'configDescriptionId', 'Tag', 0, 'b', 'c'),
('XML_MAINTABLE_ENTITIES', 'MainTable', 'dataSize', 'int', 0, 'none', 'c'),
('XML_MAINTABLE_ENTITIES', 'MainTable', 'dataUID', 'EntityRef', 0, 'none', 'c'),
('XML_MAINTABLE_ENTITIES', 'MainTable', 'execBlockId', 'Tag', 0, 'b', 'c'),
('XML_MAINTABLE_ENTITIES', 'MainTable', 'fieldId', 'Tag', 0, 'b', 'c'),
('XML_MAINTABLE_ENTITIES', 'MainTable', 'flagrow', 'string', 0, 'none', 'c'),
('XML_MAINTABLE_ENTITIES', 'MainTable', 'interval', 'Interval', 0, 'none', 'c'),
('XML_MAINTABLE_ENTITIES', 'MainTable', 'numAntenna', 'int', 0, 'none', 'c'),
('XML_MAINTABLE_ENTITIES', 'MainTable', 'numIntegration', 'int', 0, 'none', 'c'),
('XML_MAINTABLE_ENTITIES', 'MainTable', 'scanNumber', 'int', 0, 'none', 'c'),
('XML_MAINTABLE_ENTITIES', 'MainTable', 'stateId', 'Tag', 1, 'b', 'c'),
('XML_MAINTABLE_ENTITIES', 'MainTable', 'subscanNumber', 'int', 0, 'none', 'c'),
('XML_MAINTABLE_ENTITIES', 'MainTable', 'time', 'ArrayTime', 0, 'none', 'c'),
('XML_MAINTABLE_ENTITIES', 'MainTable', 'timeSampling', 'TimeSampling', 0, 'none', 'c'),
('XML_OBSERVATIONTABLE_ENTITIES', 'ObservationTable', 'observationId', 'Tag', 0, 'a', 'c'),
('XML_POINTINGMODELTABL_ENTITIES', 'PointingModelTable', 'antennaId', 'Tag', 0, 'b', 'c'),
('XML_POINTINGMODELTABL_ENTITIES', 'PointingModelTable', 'assocNature', 'String', 0, 'none', 'c'),
('XML_POINTINGMODELTABL_ENTITIES', 'PointingModelTable', 'assocPointingModelId', 'int', 0, 'b', 'c'),
('XML_POINTINGMODELTABL_ENTITIES', 'PointingModelTable', 'coeffFormula', 'String', 1, 'none', 'd'),
('XML_POINTINGMODELTABL_ENTITIES', 'PointingModelTable', 'coeffName', 'String', 1, 'none', 'c'),
('XML_POINTINGMODELTABL_ENTITIES', 'PointingModelTable', 'coeffVal', 'float', 1, 'none', 'c'),
('XML_POINTINGMODELTABL_ENTITIES', 'PointingModelTable', 'numCoeff', 'int', 0, 'none', 'c'),
('XML_POINTINGMODELTABL_ENTITIES', 'PointingModelTable', 'pointingModelId', 'int', 0, 'a', 'c'),
('XML_POINTINGMODELTABL_ENTITIES', 'PointingModelTable', 'polarizationType', 'PolarizationType', 0, 'none', 'c'),
('XML_POINTINGMODELTABL_ENTITIES', 'PointingModelTable', 'receiverBand', 'ReceiverBand', 0, 'none', 'c'),
('XML_POINTINGTABLE_ENTITIES', 'PointingTable', 'antennaId', 'Tag', 0, 'b', 'd'),
('XML_POINTINGTABLE_ENTITIES', 'PointingTable', 'atmosphericCorrection', 'Angle', 2, 'none', ''),
('XML_POINTINGTABLE_ENTITIES', 'PointingTable', 'encoder', 'Angle', 2, 'none', 'd'),
('XML_POINTINGTABLE_ENTITIES', 'PointingTable', 'numSample', 'int', 0, 'none', 'd'),
('XML_POINTINGTABLE_ENTITIES', 'PointingTable', 'numTerm', 'int', 0, 'none', 'd'),
('XML_POINTINGTABLE_ENTITIES', 'PointingTable', 'offset', 'Angle', 2, 'none', 'd'),
('XML_POINTINGTABLE_ENTITIES', 'PointingTable', 'overTheTop', 'boolean', 0, 'none', 'd'),
('XML_POINTINGTABLE_ENTITIES', 'PointingTable', 'pointingDirection', 'Angle', 2, 'none', 'd'),
('XML_POINTINGTABLE_ENTITIES', 'PointingTable', 'pointingModelId', 'int', 0, 'b', 'd'),
('XML_POINTINGTABLE_ENTITIES', 'PointingTable', 'pointingTracking', 'boolean', 0, 'none', 'd'),
('XML_POINTINGTABLE_ENTITIES', 'PointingTable', 'sampledTimeInterval', 'ArrayTimeInterval', 1, 'none', 'd'),
('XML_POINTINGTABLE_ENTITIES', 'PointingTable', 'sourceOffset', 'Angle', 2, 'none', 'd'),
('XML_POINTINGTABLE_ENTITIES', 'PointingTable', 'sourceOffsetEquinox', 'ArrayTime', 0, 'none', 'd'),
('XML_POINTINGTABLE_ENTITIES', 'PointingTable', 'sourceOffsetReferenceCode', 'DirectionReferenceCode', 0, 'none', 'd'),
('XML_POINTINGTABLE_ENTITIES', 'PointingTable', 'target', 'Angle', 2, 'none', 'd'),
('XML_POINTINGTABLE_ENTITIES', 'PointingTable', 'timeInterval', 'ArrayTimeInterval', 0, 'none', 'd'),
('XML_POINTINGTABLE_ENTITIES', 'PointingTable', 'timeOrigin', 'ArrayTime', 0, 'none', 'd'),
('XML_POINTINGTABLE_ENTITIES', 'PointingTable', 'usePolynomials', 'boolean', 0, 'none', 'd'),
('XML_POLARIZATIONTABLE_ENTITIES', 'PolarizationTable', 'corrProduct', 'PolarizationType', 2, 'none', 'c'),
('XML_POLARIZATIONTABLE_ENTITIES', 'PolarizationTable', 'corrType', 'StokesParameter', 0, 'none', 'c'),
('XML_POLARIZATIONTABLE_ENTITIES', 'PolarizationTable', 'numCorr', 'int', 0, 'none', 'c'),
('XML_POLARIZATIONTABLE_ENTITIES', 'PolarizationTable', 'polarizationId', 'Tag', 0, 'a', 'c'),
('XML_PROCESSORTABLE_ENTITIES', 'ProcessorTable', 'modeId', 'Tag', 0, 'b', 'c'),
('XML_PROCESSORTABLE_ENTITIES', 'ProcessorTable', 'processorId', 'Tag', 0, 'a', 'c'),
('XML_PROCESSORTABLE_ENTITIES', 'ProcessorTable', 'processorSubType', 'ProcessorSubType', 0, 'none', 'c'),
('XML_PROCESSORTABLE_ENTITIES', 'ProcessorTable', 'processorType', 'ProcessorType', 0, 'none', 'c'),
('XML_RECEIVERTABLE_ENTITIES', 'ReceiverTable', 'freqLO', 'Frequency', 1, 'none', 'c'),
('XML_RECEIVERTABLE_ENTITIES', 'ReceiverTable', 'frequencyBand', 'ReceiverBand', 0, 'none', 'c'),
('XML_RECEIVERTABLE_ENTITIES', 'ReceiverTable', 'name', 'String', 0, 'none', 'c'),
('XML_RECEIVERTABLE_ENTITIES', 'ReceiverTable', 'numLO', 'int', 0, 'none', 'c'),
('XML_RECEIVERTABLE_ENTITIES', 'ReceiverTable', 'receiverId', 'int', 0, 'a', 'c'),
('XML_RECEIVERTABLE_ENTITIES', 'ReceiverTable', 'receiverSideband', 'ReceiverSideband', 0, 'none', 'c'),
('XML_RECEIVERTABLE_ENTITIES', 'ReceiverTable', 'sidebandLO', 'NetSideband', 1, 'none', 'c'),
('XML_RECEIVERTABLE_ENTITIES', 'ReceiverTable', 'spectralWindowId', 'Tag', 0, 'b', 'c'),
('XML_RECEIVERTABLE_ENTITIES', 'ReceiverTable', 'timeInterval', 'ArrayTimeInterval', 0, 'none', 'c'),
('XML_SBSUMMARYTABLE_ENTITIES', 'SBSummaryTable', 'centerDirection', 'Angle', 1, 'none', 'c'),
('XML_SBSUMMARYTABLE_ENTITIES', 'SBSummaryTable', 'centerDirectionCode', 'DirectionReferenceCode', 0, 'none', 'd'),
('XML_SBSUMMARYTABLE_ENTITIES', 'SBSummaryTable', 'centerDirectionEquinox', 'ArrayTime', 0, 'none', 'd'),
('XML_SBSUMMARYTABLE_ENTITIES', 'SBSummaryTable', 'frequency', 'double', 0, 'none', 'c'),
('XML_SBSUMMARYTABLE_ENTITIES', 'SBSummaryTable', 'frequencyBand', 'ReceiverBand', 0, 'none', 'c'),
('XML_SBSUMMARYTABLE_ENTITIES', 'SBSummaryTable', 'numberRepeats', 'int', 0, 'none', 'c'),
('XML_SBSUMMARYTABLE_ENTITIES', 'SBSummaryTable', 'numObservingMode', 'int', 0, 'none', 'c'),
('XML_SBSUMMARYTABLE_ENTITIES', 'SBSummaryTable', 'numScienceGoal', 'int', 0, 'none', 'c'),
('XML_SBSUMMARYTABLE_ENTITIES', 'SBSummaryTable', 'numWeatherConstraint', 'int', 0, 'none', 'c'),
('XML_SBSUMMARYTABLE_ENTITIES', 'SBSummaryTable', 'observingMode', 'String', 1, 'none', 'c'),
('XML_SBSUMMARYTABLE_ENTITIES', 'SBSummaryTable', 'obsUnitSetUID', 'EntityRef', 0, 'b', 'c'),
('XML_SBSUMMARYTABLE_ENTITIES', 'SBSummaryTable', 'projectUID', 'EntityRef', 0, 'none', 'c'),
('XML_SBSUMMARYTABLE_ENTITIES', 'SBSummaryTable', 'sbDuration', 'Interval', 0, 'none', 'c'),
('XML_SBSUMMARYTABLE_ENTITIES', 'SBSummaryTable', 'sBSummaryId', 'Tag', 0, 'a', 'c'),
('XML_SBSUMMARYTABLE_ENTITIES', 'SBSummaryTable', 'sbSummaryUID', 'EntityRef', 0, 'none', 'c'),
('XML_SBSUMMARYTABLE_ENTITIES', 'SBSummaryTable', 'sbType', 'SBType', 0, 'none', 'c'),
('XML_SBSUMMARYTABLE_ENTITIES', 'SBSummaryTable', 'scienceGoal', 'String', 0, 'none', 'c'),
('XML_SBSUMMARYTABLE_ENTITIES', 'SBSummaryTable', 'weatherConstraint', 'String', 0, 'none', 'c'),
('XML_SCALETABLE_ENTITIES', 'ScaleTable', 'autoDataScale', 'DataScale', 0, 'none', 'c'),
('XML_SCALETABLE_ENTITIES', 'ScaleTable', 'crossDataScale', 'DataScale', 0, 'none', 'c'),
('XML_SCALETABLE_ENTITIES', 'ScaleTable', 'scaleId', 'Tag', 0, 'a', 'c'),
('XML_SCALETABLE_ENTITIES', 'ScaleTable', 'timeScale', 'TimeScale', 0, 'none', 'c'),
('XML_SCALETABLE_ENTITIES', 'ScaleTable', 'weightType', 'WeightType', 0, 'none', 'c'),
('XML_SCANTABLE_ENTITIES', 'ScanTable', 'calDataType', 'CalDataOrigin', 1, 'none', 'c'),
('XML_SCANTABLE_ENTITIES', 'ScanTable', 'calibrationFunction', 'CalibrationFunction', 0, 'none', 'd'),
('XML_SCANTABLE_ENTITIES', 'ScanTable', 'calibrationOnLine', 'boolean', 1, 'none', 'c'),
('XML_SCANTABLE_ENTITIES', 'ScanTable', 'calibrationSet', 'CalibrationSet', 1, 'none', 'd'),
('XML_SCANTABLE_ENTITIES', 'ScanTable', 'calPattern', 'AntennaMotionPattern', 0, 'none', 'd'),
('XML_SCANTABLE_ENTITIES', 'ScanTable', 'endTime', 'ArrayTime', 0, 'none', 'c'),
('XML_SCANTABLE_ENTITIES', 'ScanTable', 'execBlockId', 'Tag', 0, 'b', 'c'),
('XML_SCANTABLE_ENTITIES', 'ScanTable', 'fieldName', 'String', 0, 'none', 'd'),
('XML_SCANTABLE_ENTITIES', 'ScanTable', 'numField', 'int', 0, 'none', 'd'),
('XML_SCANTABLE_ENTITIES', 'ScanTable', 'numIntent', 'int', 0, 'none', 'c'),
('XML_SCANTABLE_ENTITIES', 'ScanTable', 'numSubscan', 'int', 0, 'none', 'c'),
('XML_SCANTABLE_ENTITIES', 'ScanTable', 'scanIntent', 'ScanIntent', 1, 'none', 'c'),
('XML_SCANTABLE_ENTITIES', 'ScanTable', 'scanNumber', 'int', 0, 'none', 'c'),
('XML_SCANTABLE_ENTITIES', 'ScanTable', 'sourceName', 'String', 0, 'none', 'd'),
('XML_SCANTABLE_ENTITIES', 'ScanTable', 'startTime', 'ArrayTime', 0, 'none', 'c'),
('XML_SEEINGTABLE_ENTITIES', 'SeeingTable', 'baseLength', 'Length', 1, 'none', 'c'),
('XML_SEEINGTABLE_ENTITIES', 'SeeingTable', 'exponent', 'float', 0, 'none', 'c'),
('XML_SEEINGTABLE_ENTITIES', 'SeeingTable', 'numBaseLength', 'int', 0, 'none', 'c'),
('XML_SEEINGTABLE_ENTITIES', 'SeeingTable', 'phaseRms', 'Angle', 1, 'none', 'c'),
('XML_SEEINGTABLE_ENTITIES', 'SeeingTable', 'seeing', 'float', 0, 'none', 'c'),
('XML_SEEINGTABLE_ENTITIES', 'SeeingTable', 'timeInterval', 'ArrayTimeInterval', 0, 'none', 'c'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'calibrationGroup', 'int', 0, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'catalog', 'String', 0, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'code', 'String', 0, 'none', 'c'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'deltaVel', 'Speed', 0, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'direction', 'Angle', 1, 'none', 'c'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'directionCode', 'DirectionReferenceCode', 0, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'directionEquinox', 'ArrayTime', 0, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'flux', 'Flux', 2, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'fluxErr', 'Flux', 2, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'frequency', 'Frequency', 1, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'frequencyInterval', 'Frequency', 1, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'frequencyRefCode', 'FrequencyReferenceCode', 0, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'numFreq', 'int', 0, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'numLines', 'int', 0, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'numStokes', 'int', 0, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'position', 'Length', 1, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'positionAngle', 'Angle', 1, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'positionAngleErr', 'Angle', 1, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'properMotion', 'AngularRate', 1, 'none', 'c'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'rangeVel', 'Speed', 1, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'restFrequency', 'Frequency', 1, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'sizeErr', 'Angle', 2, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'size', 'Angle', 2, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'sourceId', 'int', 0, 'a', 'c'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'sourceModel', 'SourceModel', 0, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'sourceName', 'String', 0, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'spectralWindowId', 'Tag', 0, 'b', 'c'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'stokesParameter', 'StokesParameter', 1, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'sysVel', 'Speed', 1, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'timeInterval', 'ArrayTimeInterval', 0, 'none', 'c'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'transition', 'String', 1, 'none', 'd'),
('XML_SOURCETABLE_ENTITIES', 'SourceTable', 'velRefCode', 'RadialVelocityReferenceCode', 0, 'none', 'd'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'assocNature', 'SpectralResolutionType', 1, 'none', 'd'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'assocSpectralWindowId', 'Tag', 1, 'b', 'd'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'basebandName', 'BasebandName', 0, 'none', 'c'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'chanFreqArray', 'Frequency', 1, 'none', 'd'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'chanFreqStart', 'Frequency', 0, 'none', 'd'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'chanFreqStep', 'Frequency', 0, 'none', 'd'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'chanWidth', 'Frequency', 0, 'none', 'd'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'chanWidthArray', 'Frequency', 1, 'none', 'd'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'correlationBit', 'CorrelationBit', 0, 'none', 'd'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'dopplerId', 'int', 0, 'b', 'd'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'effectiveBw', 'Frequency', 0, 'none', 'd'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'effectiveBwArray', 'Frequency', 1, 'none', 'd'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'freqGroup', 'int', 0, 'none', 'd'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'freqGroupName', 'String', 0, 'none', 'd'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'imageSpectralWindowId', 'Tag', 0, 'b', 'd'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'lineArray', 'boolean', 1, 'none', 'd'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'measFreqRef', 'FrequencyReferenceCode', 0, 'none', 'd'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'name', 'String', 0, 'none', 'd'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'netSideband', 'NetSideband', 0, 'none', 'c'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'numAssocValues', 'int', 0, 'none', 'd'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'numChan', 'int', 0, 'none', 'c'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'oversampling', 'boolean', 0, 'none', 'd'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'quantization', 'boolean', 0, 'none', 'd'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'refChan', 'double', 0, 'none', 'd'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'refFreq', 'Frequency', 0, 'none', 'c'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'resolution', 'Frequency', 0, 'none', 'd'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'resolutionArray', 'Frequency', 1, 'none', 'd'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'sidebandProcessingMode', 'SidebandProcessingMode', 0, 'none', 'c'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'spectralWindowId', 'Tag', 0, 'a', 'c'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'totBandwidth', 'Frequency', 0, 'none', 'c'),
('XML_SPECTRALWINDOWTAB_ENTITIES', 'SpectralWindowTable', 'windowFunction', 'WindowFunction', 0, 'none', 'c'),
('XML_SQUARELAWDETECTOR_ENTITIES', 'SquareLawDetectorTable', 'bandType', 'DetectorBandType', 0, 'none', 'c'),
('XML_SQUARELAWDETECTOR_ENTITIES', 'SquareLawDetectorTable', 'numBand', 'int', 0, 'none', 'c'),
('XML_SQUARELAWDETECTOR_ENTITIES', 'SquareLawDetectorTable', 'squareLawDetectorId', 'Tag', 0, 'a', 'c'),
('XML_STATETABLE_ENTITIES', 'StateTable', 'calDeviceName', 'CalibrationDevice', 0, 'none', 'c'),
('XML_STATETABLE_ENTITIES', 'StateTable', 'onSky', 'boolean', 0, 'none', 'c'),
('XML_STATETABLE_ENTITIES', 'StateTable', 'ref', 'boolean', 0, 'none', 'c'),
('XML_STATETABLE_ENTITIES', 'StateTable', 'sig', 'boolean', 0, 'none', 'c'),
('XML_STATETABLE_ENTITIES', 'StateTable', 'stateId', 'Tag', 0, 'a', 'c'),
('XML_STATETABLE_ENTITIES', 'StateTable', 'weight', 'float', 0, 'none', 'd'),
('XML_STATIONTABLE_ENTITIES', 'StationTable', 'name', 'String', 0, 'none', 'c'),
('XML_STATIONTABLE_ENTITIES', 'StationTable', 'position', 'Length', 1, 'none', 'c'),
('XML_STATIONTABLE_ENTITIES', 'StationTable', 'stationId', 'Tag', 0, 'a', 'c'),
('XML_STATIONTABLE_ENTITIES', 'StationTable', 'time', 'ArrayTime', 0, 'none', 'd'),
('XML_STATIONTABLE_ENTITIES', 'StationTable', 'type', 'StationType', 0, 'none', 'c'),
('XML_SUBSCANTABLE_ENTITIES', 'SubscanTable', 'correlatorCalibration', 'CorrelatorCalibration', 0, 'none', 'd'),
('XML_SUBSCANTABLE_ENTITIES', 'SubscanTable', 'endTime', 'ArrayTime', 0, 'none', 'c'),
('XML_SUBSCANTABLE_ENTITIES', 'SubscanTable', 'execBlockId', 'Tag', 0, 'b', 'c'),
('XML_SUBSCANTABLE_ENTITIES', 'SubscanTable', 'fieldName', 'String', 0, 'none', 'd'),
('XML_SUBSCANTABLE_ENTITIES', 'SubscanTable', 'numIntegration', 'int', 0, 'none', 'c'),
('XML_SUBSCANTABLE_ENTITIES', 'SubscanTable', 'numSubintegration', 'int', 1, 'none', 'c'),
('XML_SUBSCANTABLE_ENTITIES', 'SubscanTable', 'scanNumber', 'int', 0, 'none', 'c'),
('XML_SUBSCANTABLE_ENTITIES', 'SubscanTable', 'startTime', 'ArrayTime', 0, 'none', 'c'),
('XML_SUBSCANTABLE_ENTITIES', 'SubscanTable', 'subscanIntent', 'SubscanIntent', 0, 'none', 'c'),
('XML_SUBSCANTABLE_ENTITIES', 'SubscanTable', 'subscanMode', 'SwitchingMode', 0, 'none', 'd'),
('XML_SUBSCANTABLE_ENTITIES', 'SubscanTable', 'subscanNumber', 'int', 0, 'none', 'c'),
('XML_SWITCHCYCLETABLE_ENTITIES', 'SwitchCycleTable', 'directionCode', 'DirectionReferenceCode', 0, 'none', 'd'),
('XML_SWITCHCYCLETABLE_ENTITIES', 'SwitchCycleTable', 'directionEquinox', 'ArrayTime', 0, 'none', 'd'),
('XML_SWITCHCYCLETABLE_ENTITIES', 'SwitchCycleTable', 'dirOffsetArray', 'Angle', 2, 'none', 'c'),
('XML_SWITCHCYCLETABLE_ENTITIES', 'SwitchCycleTable', 'freqOffsetArray', 'Frequency', 1, 'none', 'c'),
('XML_SWITCHCYCLETABLE_ENTITIES', 'SwitchCycleTable', 'numStep', 'int', 0, 'none', 'c'),
('XML_SWITCHCYCLETABLE_ENTITIES', 'SwitchCycleTable', 'stepDurationArray', 'Interval', 1, 'none', 'c'),
('XML_SWITCHCYCLETABLE_ENTITIES', 'SwitchCycleTable', 'switchCycleId', 'Tag', 0, 'a', 'c'),
('XML_SWITCHCYCLETABLE_ENTITIES', 'SwitchCycleTable', 'weightArray', 'float', 1, 'none', 'c'),
('XML_SYSCALTABLE_ENTITIES', 'SysCalTable', 'antennaId', 'Tag', 0, 'b', 'c'),
('XML_SYSCALTABLE_ENTITIES', 'SysCalTable', 'feedId', 'int', 0, 'b', 'c'),
('XML_SYSCALTABLE_ENTITIES', 'SysCalTable', 'numChan', 'int', 0, 'none', 'c'),
('XML_SYSCALTABLE_ENTITIES', 'SysCalTable', 'numReceptor', 'int', 0, 'none', 'c'),
('XML_SYSCALTABLE_ENTITIES', 'SysCalTable', 'phaseDiffFlag', 'boolean', 0, 'none', 'd'),
('XML_SYSCALTABLE_ENTITIES', 'SysCalTable', 'phaseDiffSpectrum', 'float', 2, 'none', 'd'),
('XML_SYSCALTABLE_ENTITIES', 'SysCalTable', 'spectralWindowId', 'Tag', 0, 'b', 'c'),
('XML_SYSCALTABLE_ENTITIES', 'SysCalTable', 'tantFlag', 'boolean', 0, 'none', 'd'),
('XML_SYSCALTABLE_ENTITIES', 'SysCalTable', 'tantSpectrum', 'float', 2, 'none', 'd'),
('XML_SYSCALTABLE_ENTITIES', 'SysCalTable', 'tantTsysFlag', 'boolean', 0, 'none', 'd'),
('XML_SYSCALTABLE_ENTITIES', 'SysCalTable', 'tantTsysSpectrum', 'float', 2, 'none', 'd'),
('XML_SYSCALTABLE_ENTITIES', 'SysCalTable', 'tcalFlag', 'boolean', 0, 'none', 'd'),
('XML_SYSCALTABLE_ENTITIES', 'SysCalTable', 'tcalSpectrum', 'Temperature', 2, 'none', 'd'),
('XML_SYSCALTABLE_ENTITIES', 'SysCalTable', 'timeInterval', 'ArrayTimeInterval', 0, 'none', 'c'),
('XML_SYSCALTABLE_ENTITIES', 'SysCalTable', 'trxFlag', 'boolean', 0, 'none', 'd'),
('XML_SYSCALTABLE_ENTITIES', 'SysCalTable', 'trxSpectrum', 'Temperature', 2, 'none', 'd'),
('XML_SYSCALTABLE_ENTITIES', 'SysCalTable', 'tskyFlag', 'boolean', 0, 'none', 'd'),
('XML_SYSCALTABLE_ENTITIES', 'SysCalTable', 'tskySpectrum', 'Temperature', 2, 'none', 'd'),
('XML_SYSCALTABLE_ENTITIES', 'SysCalTable', 'tsysFlag', 'boolean', 0, 'none', 'd'),
('XML_SYSCALTABLE_ENTITIES', 'SysCalTable', 'tsysSpectrum', 'Temperature', 2, 'none', 'd'),
('XML_TOTALPOWERTABLE_ENTITIES', 'TotalPowerTable', 'configDescriptionId', 'Tag', 0, 'b', 'c'),
('XML_TOTALPOWERTABLE_ENTITIES', 'TotalPowerTable', 'execBlockId', 'Tag', 0, 'b', 'c'),
('XML_TOTALPOWERTABLE_ENTITIES', 'TotalPowerTable', 'exposure', 'Interval', 2, 'none', 'c'),
('XML_TOTALPOWERTABLE_ENTITIES', 'TotalPowerTable', 'fieldId', 'Tag', 0, 'b', 'c'),
('XML_TOTALPOWERTABLE_ENTITIES', 'TotalPowerTable', 'flagAnt', 'int', 1, 'none', 'c'),
('XML_TOTALPOWERTABLE_ENTITIES', 'TotalPowerTable', 'flagPol', 'int', 2, 'none', 'c'),
('XML_TOTALPOWERTABLE_ENTITIES', 'TotalPowerTable', 'floatData', 'float', 3, 'none', 'c'),
('XML_TOTALPOWERTABLE_ENTITIES', 'TotalPowerTable', 'integrationNumber', 'int', 0, 'none', 'c'),
('XML_TOTALPOWERTABLE_ENTITIES', 'TotalPowerTable', 'interval', 'Interval', 0, 'none', 'c'),
('XML_TOTALPOWERTABLE_ENTITIES', 'TotalPowerTable', 'scanNumber', 'int', 0, 'none', 'c'),
('XML_TOTALPOWERTABLE_ENTITIES', 'TotalPowerTable', 'stateId', 'Tag', 1, 'b', 'c'),
('XML_TOTALPOWERTABLE_ENTITIES', 'TotalPowerTable', 'subintegrationNumber', 'int', 0, 'none', 'd'),
('XML_TOTALPOWERTABLE_ENTITIES', 'TotalPowerTable', 'subscanNumber', 'int', 0, 'none', 'c'),
('XML_TOTALPOWERTABLE_ENTITIES', 'TotalPowerTable', 'time', 'ArrayTime', 0, 'none', 'c'),
('XML_TOTALPOWERTABLE_ENTITIES', 'TotalPowerTable', 'timeCentroid', 'ArrayTime', 2, 'none', 'c'),
('XML_TOTALPOWERTABLE_ENTITIES', 'TotalPowerTable', 'uvw', 'Length', 2, 'none', 'c'),
('XML_WEATHERTABLE_ENTITIES', 'WeatherTable', 'cloudMonitor', 'Temperature', 0, 'none', 'd'),
('XML_WEATHERTABLE_ENTITIES', 'WeatherTable', 'dewPoint', 'Temperature', 0, 'none', 'd'),
('XML_WEATHERTABLE_ENTITIES', 'WeatherTable', 'layerHeight', 'Length', 1, 'none', 'd'),
('XML_WEATHERTABLE_ENTITIES', 'WeatherTable', 'numLayer', 'int', 0, 'none', 'd'),
('XML_WEATHERTABLE_ENTITIES', 'WeatherTable', 'numWVR', 'int', 0, 'none', 'd'),
('XML_WEATHERTABLE_ENTITIES', 'WeatherTable', 'pressure', 'Pressure', 0, 'none', 'c'),
('XML_WEATHERTABLE_ENTITIES', 'WeatherTable', 'relHumidity', 'Humidity', 0, 'none', 'c'),
('XML_WEATHERTABLE_ENTITIES', 'WeatherTable', 'stationId', 'Tag', 0, 'b', 'c'),
('XML_WEATHERTABLE_ENTITIES', 'WeatherTable', 'temperature', 'Temperature', 0, 'none', 'c'),
('XML_WEATHERTABLE_ENTITIES', 'WeatherTable', 'temperatureProfile', 'Temperature', 1, 'none', 'd'),
('XML_WEATHERTABLE_ENTITIES', 'WeatherTable', 'timeInterval', 'ArrayTimeInterval', 0, 'none', 'c'),
('XML_WEATHERTABLE_ENTITIES', 'WeatherTable', 'water', 'double', 0, 'none', 'd'),
('XML_WEATHERTABLE_ENTITIES', 'WeatherTable', 'windDirection', 'Angle', 0, 'none', 'c'),
('XML_WEATHERTABLE_ENTITIES', 'WeatherTable', 'windMax', 'Speed', 0, 'none', 'c'),
('XML_WEATHERTABLE_ENTITIES', 'WeatherTable', 'windSpeed', 'Speed', 0, 'none', 'c'),
('XML_WEATHERTABLE_ENTITIES', 'WeatherTable', 'wvrTemp', 'Temperature', 1, 'none', 'd'),
('XML_WVMCALTABLE_ENTITIES', 'WVMCalTable', 'antennaId', 'Tag', 0, 'b', 'c'),
('XML_WVMCALTABLE_ENTITIES', 'WVMCalTable', 'numChan', 'int', 0, 'none', 'c'),
('XML_WVMCALTABLE_ENTITIES', 'WVMCalTable', 'numinputantenna', 'int', 0, 'none', 'c'),
('XML_WVMCALTABLE_ENTITIES', 'WVMCalTable', 'numPoly', 'int', 0, 'none', 'c'),
('XML_WVMCALTABLE_ENTITIES', 'WVMCalTable', 'pathCoeff', 'double', 2, 'none', 'c'),
('XML_WVMCALTABLE_ENTITIES', 'WVMCalTable', 'polyFreqLimits', 'Frequency', 1, 'none', 'c'),
('XML_WVMCALTABLE_ENTITIES', 'WVMCalTable', 'refTemp', 'double', 1, 'none', 'c'),
('XML_WVMCALTABLE_ENTITIES', 'WVMCalTable', 'spectralWindowId', 'Tag', 0, 'b', 'c'),
('XML_WVMCALTABLE_ENTITIES', 'WVMCalTable', 'timeInterval', 'ArrayTimeInterval', 0, 'none', 'c'),
('XML_WVMCALTABLE_ENTITIES', 'WVMCalTable', 'wvrMethod', 'WVRMethod', 0, 'none', 'c')]

def typemap(type, typefrom='aida', typeto='postgres'):
	if typefrom == 'aida':
		if typeto == 'postgres':
			if type == 'int':
				return('bigint')
			elif type == 'str':
				return('text')
			elif type == 'float':
				return('double precision')
			else:
				return('text')

	if typefrom == 'aida':
		if typeto == 'sqlite':
			if type == 'int':
				return('integer')
			elif type == 'str':
				return('text')
			elif type == 'float':
				return('real')
			else:
				return('text')
	

	if typefrom == 'oracle':
		from cx_Oracle import STRING, NUMBER
		
		if typeto == 'sqlite':
			if type is STRING:
				return('text')
			elif type is NUMBER:
				return('real')
			else:
				return('text')

# Load conf file

def create_conn_metadata_sco():
	from cx_Oracle import connect
	from .archiveConf import db
	global conn_metadata
	conn_metadata = connect(db['sco'])

def create_conn_metadata_osf():
	from cx_Oracle import connect
	from .archiveConf import db
	global conn_metadata
	conn_metadata = connect(db['osf'])

def create_conn_aidadb():
	from psycopg2 import connect
	global conn_aidadb
	from .archiveConf import db
	conn_aidadb = connect(db['aidadb'])

def conn_aidadb_close():
	conn_aidadb.close()

# Global variables
from sqlite3 import connect as sqlite_connect
global ramdb_conn
ramdb_conn = sqlite_connect(":memory:")
global conn_aidadb

# TODO: delete the following commented-out lines
#from .archiveConf import ngas_default
#global ngassrv
#ngassrv = ngas_default
#if __name__ == "__main__":
#	from cx_Oracle import connect
#	global conn_metadata
#	conn_metadata = connect(archiveConf.conn_metadata_default)
	
		

