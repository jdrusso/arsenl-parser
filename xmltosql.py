import psycopg2 as sql
import xml.etree.ElementTree as ET
import re, sys, os


def formatDate(date):
	#Formats an input date in format ex "20140716_123133"
	year = date[:4]
	month = date[4:6]
	day = date[6:8]

	hour = date[9:11]
	minute = date[11:13]
	second = date[13:15]

	return ("%s/%s/%s %s:%s.%s" % (day, month, year, hour, minute, second))
class XMLParser():

	def __init__(self, dbuser, password, testResults="../nosetests.xml", dbname="results"):

		self.conn = sql.connect("dbname=%s user=%s password=%s" % (dbname, dbuser, password))
		self.cursor = self.conn.cursor()
		print("Connected")

		self.xmlTree = ET.parse(testResults)
		self.xmlRoot = self.xmlTree.getroot()

		self.conn.commit()

	def parse(self):

		run_num = 0

		self.cursor.execute('SELECT MAX(run_num) FROM test_result;')

		try:
			run_num = self.cursor.fetchone()[0] + 1
		except TypeError:
			run_num = 0

		print("Run_num is %d" % run_num)

		for child in self.xmlRoot:

			if 'teardown' in child.attrib['name']:
				continue
			if 'setup' in child.attrib['name']:
				continue

			self.cursor.execute('SELECT MAX(test_result_id) FROM test_result;')
			try:
				id_num = int(self.cursor.fetchone()[0] + 1)
			except TypeError:
				id_num = 0

			self.cursor.execute('SELECT MAX(test_result_id) FROM test_result;')
			try:
				id_num = int(self.cursor.fetchone()[0] + 1)
			except TypeError:
				id_num = 0

			self.cursor.execute('SELECT MAX(test_result_id) FROM test_result;')
			try:
				id_num = int(self.cursor.fetchone()[0] + 1)
			except TypeError:
				id_num = 0

			name = child.attrib['name']
			print("Parsing child %s" % name)
			testType = re.split('_', child.attrib['classname'])[0]
			time = child.attrib['time']

			SHA_list = child.attrib['sha_list']

			date = child.attrib['datestamp']
			dateString = re.sub(' ', '_', re.sub('[-:]', '', date))


			xml_path = name + "_" + dateString + '.xml'
			xmlName = name

			if 'test_enter_modes' in name:
				xmlName = 'test_enter_modes'

			xml_file = open(xml_path, 'w+')
			xml_name = ET.Element(name, {"name" : name})

			try:
				mavout = ET.SubElement(xml_name, 'MAVProxy-out')
				mavout.text = child.find('MAVProxy-out').text
			except AttributeError:
				print('Attribute %s does not exist for %s' % ('mavout', name))

			try:
				jsbout = ET.SubElement(xml_name, 'JSBSim-out')
				jsbout.text = child.find('JSBSim-out').text
			except AttributeError:
				print('Attribute %s does not exist for %s' % ('jsbout', name))

			try:
				sysout = ET.SubElement(xml_name, 'system-out')
				sysout.text = child.find('system-out').text
			except AttributeError:
				print('Attribute %s does not exist for %s' % ('sysout', name))

			xml_file.write(ET.tostring(xml_name))

			self.cursor.execute('''INSERT INTO test_case 
				SELECT %(name)s, %(function)s, %(test_type)s
				WHERE NOT EXISTS (SELECT 1 FROM test_case WHERE test_function=%(function)s);''',
				{
				'name' : child.attrib['name'],
				'function' : child.attrib['name'],
				'test_type' : testType
				})
			self.conn.commit()

			try:
				self.cursor.execute('SELECT test_case_id FROM test_case WHERE (test_function = %s);', (child.attrib['name'],))
				caseID = self.cursor.fetchone()[0]
			except Exception as e:
				print("Exception in test_case_id lookup: %s" % e)
				caseID = -1

			self.cursor.execute('''INSERT INTO test_result 
				VALUES (%(datestamp)s, %(run_num)s, %(run_time)s, %(result)s, 
					%(test_case_id)s, %(project_id)s, %(sha_list)s, %(xml_path)s);''',
				{
				'datestamp': formatDate(dateString),
				'run_num':run_num,
				'run_time':float(child.attrib['time']),
				'result':child.attrib['status'],
				'test_case_id':caseID,
				'project_id':1,
				'sha_list':SHA_list,
				'xml_path':xml_path,
				})

	def finalize(self):

		self.conn.commit()
		self.conn.close()

def main(argv):

	try:
		path = sys.argv[1]
	except IndexError:
		path = None
	
	try:
		CURRENT_DIR = os.path.dirname(__file__)
		login_path = os.path.join(CURRENT_DIR, 'LOGIN')
		creds = open(login_path)
		username = creds.readline().rstrip()[5:]
		password = creds.readline().rstrip()[5:]

		if username == '[username]' or password == '[password]':
			print('Please enter your DB username and password in LOGIN, in the same folder as this script.')
			return

	except Exception:
		print('Could not read credentials')
		return -1

	if not path == None:
		parser = XMLParser(dbuser=username, password=password, testResults=path)
	else: 
		parser = XMLParser(dbuser=username, password=password)


	parser.parse()
	parser.finalize()

if __name__ == "__main__":
	main(sys.argv[1:])