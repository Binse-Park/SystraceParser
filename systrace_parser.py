import numpy as np
from pandas import Series, DataFrame
import copy

TRACE_MARK = 'tracing_mark_write:'
SCHED_SWITCH = 'sched_switch:'
SCHED_WAKEUP = 'sched_wakeup:'
SCHED_BLOCKED_REASON = 'sched_blocked_reason:'
CPU_FREQUENCY_LIMITS = 'cpu_frequency_limits:'
CPU_IDLE = 'cpu_idle:'

TAG_RUNNING = 'RUNNING'
TAG_RUNNABLE = 'RUNNABLE'
TAG_SLEEPING = 'SLEEPING'
TAG_UNINTERUPTIBLE_SLEEP = 'UNINTERUPTIBLE_SLEEP'
TAG_UNINTERUPTIBLE_SLEEP_IO = 'UNINTERUPTIBLE_SLEEP(I/O)'
TAG_CORE_IDLE = 'I'
TAG_CORE_RUNNING = 'R'

##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
#	DEFINE CLASS FOR HIERACHY IN THE PARSER
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################

class hierarchy:
	@staticmethod
	def open(current_time):
		hnd = dict()
		hnd['time'] = current_time
		hnd['start_time'] = current_time
		hnd['sched_time'] = current_time
		hnd['on_process'] = True
		return hnd

	@staticmethod
	def close(hnd, current_time):
		hnd['time'] = current_time - hnd['time']
		hnd['end_time'] = current_time
		hnd['on_process'] = False
		hnd[TAG_RUNNING] = hnd.get(TAG_RUNNING, 0) + (current_time - hnd['sched_time'])

	@staticmethod
	def set(hnd, set_data, result_core_state, storage_lock_contention):
		#if 'next_comm' in set_data:	
		#	print("time : {}  next_comm : {}  tag : {}".format(set_data['time'], set_data['next_comm'], set_data['tag']))
		#result_core_state = class_parser_range.result_core_state
		if len(hnd) > 0:
			hnd = hnd[-1]
		if 'on_process' in hnd and hnd['on_process']:
			######## Update process's state
			tag = set_data['tag']
			if tag == TAG_UNINTERUPTIBLE_SLEEP: 
				hnd['process_state'] = tag
				hnd['uninter_reason'] = hnd.get('uninter_reason', dict())
				hnd['uninter_reason'][set_data['caller']] = hnd['uninter_reason'].get(set_data['caller'], 0) + 1
			elif tag == TAG_UNINTERUPTIBLE_SLEEP_IO:
				hnd['process_state'] = tag
				hnd['uninter_reason_io'] = hnd.get('uninter_reason_io', dict())
				hnd['uninter_reason_io'][set_data['caller']] = hnd['uninter_reason_io'].get(set_data['caller'], 0) + 1
			else:
				if 'process_state' in hnd and len(hnd['process_state']) > 0:
					tag = hnd['process_state']
					hnd['process_state'] = ''

				sched_time = hnd['sched_time']
				######## Update processing time
				hnd[tag] = hnd.get(tag, 0) + (set_data['time'] - hnd['sched_time'])
				hnd['sched_time'] = set_data['time']
				######## Update core number
				if tag == TAG_RUNNING:
					hnd['core'] = hnd.get('core', [0] * 8)  #conf["MAX_CORE_NUM"]
					if set_data['core'] < 8:  #conf["MAX_CORE_NUM"]:
						hnd['core'][set_data['core']] += 1
				elif tag == TAG_RUNNABLE:
					core_state = copy.deepcopy(result_core_state)
					core_state['time'] = set_data['time']
					core_state['selected'] = set_data['core']
					core_state[core_state['selected']] = 'V'
					hnd['stat_core'] = hnd.get('stat_core', list())
					hnd['stat_core'].append(core_state)
				elif tag == TAG_SLEEPING:
					#print("current time : {}   sched_time : {}-----------------------------------------------------".format( set_data['time'], sched_time ))
					#display(storage_lock_contention)
					found_flag = False
					for lock_contention in storage_lock_contention:
						if 'duration' in lock_contention:
							#print("lock_contention time : {}".format( lock_contention['time'] ))
							if lock_contention['time'] > sched_time:
								lock_contention['effection'] = 'O'
								found_flag = True
					if found_flag:
						hnd['lock_contention'] = hnd.get('lock_contention', 0) + (set_data['time'] - sched_time)
						#display(hnd['lock_contention'])

	@staticmethod
	def get_from_index(hnd, index):
		#print(index + '/' + index[:4])
		if index[:4] == 'core' and 'core' in hnd:
			core_num = int(index[-1])
			if core_num > len(hnd['core']):
				return 0
			else:
				return hnd['core'][core_num]
		
		depth = index.split('//')
		if len(depth) > 1 and depth[0] in hnd:
			return hnd[depth[0]].get(depth[1], 0)
		#print(hnd.get(index, 0))
		return hnd.get(index, 0)

	@staticmethod
	def get(hnd, get_data, num=-1):
		column_data = [0] * len(get_data)
		if num >= 0:
			column_data = [hierarchy.get_from_index(hnd[num], idx) for idx in get_data]
		else:
			for num in hnd:
				column_data = map(np.add, column_data, [hierarchy.get_from_index(num, idx) for idx in get_data])
		return column_data


	@staticmethod
	def get_rawdata(hnd, index, num=-1):
		if num >= 0:
			item = hnd[num]
			if index in item:
				return item[index]
		else:
			for item in hnd:
				if index in item:
					return item[index]
		return 0

	@staticmethod
	def unint_sleep(hnd, num=-1):
		depthes = ['uninter_reason', 'uninter_reason_io']
		index_data = list()
		if num >= 0:
			for element in hnd[num]:
				for depth in depthes:
					if depth in hnd[num]:
						for element in hnd[num][depth]:
							index_data.append('{}//{}'.format(depth, element))
		else:
			for num in hnd:
				for depth in depthes:
					if depth in num:
						for element in num[depth]:
							index_data.append('{}//{}'.format(depth, element))
		return index_data

##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
#	DEFINE CLASS FOR THE PARSER
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
class parser_range:

	def __init__(self, trace_mark_filters, raw_data, title):
		self.trace_mark_filters = trace_mark_filters
		self.raw_data = raw_data
		self.title = title
		self.result_times = dict()   # Storing the time data.
		self.trace_mark_traversal = dict() # Storing the systrace tag's context to check end of it.
		self.result_cores = dict() # Storing a data to be expected for marking.
		self.result_core_state = dict()
		self.storage_lock_contention = list()

	def parser_trace_mark(self, str):
		result = dict()
		trace_mark = str.split(TRACE_MARK)

		if len(trace_mark) > 0:
			before_trace_mark = trace_mark[0].split(' ')
		try:
			result['time'] = float(before_trace_mark[-2].strip(':'))
		except:
			result['time'] = 0.0

		try:
			if not 'pid' in result:
				result['pid'] = int(trace_mark[0][17:22].strip())
		except:
			pass

		try:
			if not 'pid' in result:
				result['pid'] = int(trace_mark[0][24:29].strip())
		except:
			pass

		if len(trace_mark) > 1:
			after_trace_mark = trace_mark[1].split('|')
			result['type'] = after_trace_mark[0].strip()
		if len(after_trace_mark) > 1 :
			if not 'pid' in result or result['type'] == 'S' or result['type'] == 'F':
				result['pid'] = int(after_trace_mark[1].strip())
		if len(after_trace_mark) > 2:
			result['context'] = after_trace_mark[2].strip()

		return result

	def trace_mark_func(self, str):
		trace_mark = self.parser_trace_mark(str)
		if 'pid' in trace_mark and 'type' in trace_mark:
			self.trace_mark_traversal[trace_mark['pid']] = self.trace_mark_traversal.get(trace_mark['pid'], list())
			if trace_mark['type'] == 'B':
				self.trace_mark_traversal[trace_mark['pid']].append(trace_mark['context'])
				if 'monitor contention with owner' in trace_mark['context']:
					self.storage_lock_contention.append(trace_mark);
					#display(trace_mark)
					#for pid in self.result_times:
					#	for trace_mark_filter in self.result_times[pid]:
					#		display(self.result_times[pid][trace_mark_filter])
			elif trace_mark['type'] == 'E' and len(self.trace_mark_traversal[trace_mark['pid']]) > 0:
				trace_mark['context'] = self.trace_mark_traversal[trace_mark['pid']][-1]
				self.trace_mark_traversal[trace_mark['pid']] = self.trace_mark_traversal[trace_mark['pid']][0 : -1]
				if 'monitor contention with owner' in trace_mark['context']:
					for lock_contention in self.storage_lock_contention:
						if not 'duration' in lock_contention:
							if lock_contention['pid'] == trace_mark['pid']:
								lock_contention['duration'] = trace_mark['time'] - lock_contention['time']
								#display(lock_contention)
			#elif '18805' in str:
			#	print('>>>>>>>>>>>>>>>>' + str)
		#elif '18805' in str:
		#	print('>>>>>>>>>>>>>>>>' + str)
		for trace_mark_filter in self.trace_mark_filters:
			for se_mark in self.trace_mark_filters[trace_mark_filter]:
				cur_filter = self.trace_mark_filters[trace_mark_filter][se_mark]

				try:
					if cur_filter['context'] in trace_mark['context'] and cur_filter['type'] in trace_mark['type']:
						pid = trace_mark['pid']
						self.result_times[pid] = self.result_times.get(pid, dict())
						if not trace_mark_filter in self.result_times[pid]:
							self.result_times[pid][trace_mark_filter] = list()
						if se_mark == 'SMARK':
							self.result_times[pid][trace_mark_filter].append(hierarchy.open(trace_mark['time']))
						elif se_mark == 'EMARK':
							hierarchy.close(self.result_times[pid][trace_mark_filter][-1], trace_mark['time'])
						#if '18805' in str:
						#    print('--------' + str)
				except:
					#if '18805' in str:
					#    print(str)
					#    print(trace_mark)
					pass
				#if 'launching:' in str:
				#    print(str)
				#    print(trace_mark)
		#    else:
		#        print(str)
		#        print(trace_mark)



##################################################################################################################################################################
#	DEFINE FUNCTIONS FOR CORRECTING DATA 
##################################################################################################################################################################

	def parser_correct_mark(self, str):
		result = dict()
		str = str.strip()
		trace_items = str.split(': ')
		if len(trace_items) > 1:
			type_filter = trace_items[1]
		
		trace_items = str.split(' ')
		for trace_item in trace_items:
			if '=' in trace_item:
				trace_item = trace_item.split('=')
				result[trace_item[0]] = trace_item[1]

		trace_marks = str.split(': ' + type_filter)
		trace_marks = trace_marks[0].split(' ')

		try:
			result['time'] = float(trace_marks[-1])
		except:
			pass

		for trace_mark in trace_marks:
			if '[' in trace_mark and ']' in trace_mark and len(trace_mark) == 5:
				try :
					result['core'] = int(trace_mark.strip('[]'))
				except:
					pass
		return result, type_filter

	def correct_func(self, str):
		correct_mark_itemes, type_filter = self.parser_correct_mark(str)
		type_filter = type_filter + ':'
		self.result_cores[type_filter] = self.result_cores.get(type_filter, dict())

		for correct_mark_item in correct_mark_itemes:
			self.result_cores[type_filter][correct_mark_item] = self.result_cores[type_filter].get(correct_mark_item, list())
			self.result_cores[type_filter][correct_mark_item].append(correct_mark_itemes[correct_mark_item])

##################################################################################################################################################################
#	DEFINE FUNCTIONS FOR SCHED PARSER
##################################################################################################################################################################

	def parser_sched(self, str):
		result = dict()
		str = str.strip()
		sched_items = str.split(' ')
		for sched_item in sched_items:
			if '=' in sched_item:
				sched_item = sched_item.split('=')
				result[sched_item[0]] = sched_item[1]

		sched_marks = str.split(': sched_')
		sched_marks = sched_marks[0].split(' ')
		result['time'] = float(sched_marks[-1])
		for sched_mark in sched_marks:
			if '[' in sched_mark and ']' in sched_mark and len(sched_mark) == 5:
				try :
					result['core'] = int(sched_mark.strip('[]'))
				except:
					pass
		return result

	def update_sched_time(self, sched_itemes, pid):
		if 'prev_state' in sched_itemes:
			if sched_itemes['prev_state'] == 'R':
				self.result_core_state[sched_itemes['core']] = TAG_CORE_RUNNING
			else: #if sched_itemes['prev_state'] == 'D':
				self.result_core_state[sched_itemes['core']] = TAG_CORE_IDLE
		#if 'next_comm' in sched_itemes:
		#	print("update_sched_time -> time : {}  next_comm : {}  tag : {}  core : {}  curstate : {}".format(sched_itemes['time'], sched_itemes['next_comm'], sched_itemes['tag'], sched_itemes['core'], self.result_core_state))

		if pid in self.result_times:
			#self.result_times[pid] = self.result_times.get(pid, dict())
			for trace_mark_filter in self.result_times[pid]:
				#print("before {}".format(self.result_core_state))
				hierarchy.set(self.result_times[pid][trace_mark_filter], sched_itemes, self.result_core_state, self.storage_lock_contention)
				#print("after {}".format(self.result_core_state))

	def sched_switch_func(self, str):
		sched_itemes = self.parser_sched(str)
		#print("sched_switch_func -> time : {}  next_comm : {}".format(sched_itemes['time'], sched_itemes['next_comm']))
		if 'prev_pid' in sched_itemes:
			sched_itemes['tag'] = TAG_RUNNING
			self.update_sched_time(sched_itemes, int(sched_itemes['prev_pid']))
		if 'next_pid' in sched_itemes:
			sched_itemes['tag'] = TAG_RUNNABLE
			self.update_sched_time(sched_itemes, int(sched_itemes['next_pid']))

	def sched_wakeup_func(self, str):
		sched_itemes = self.parser_sched(str)
		if 'pid' in sched_itemes:
			sched_itemes['tag'] = TAG_SLEEPING
			self.update_sched_time(sched_itemes, int(sched_itemes['pid']))

	def sched_blocked_reason(self, str):
		sched_itemes = self.parser_sched(str)
		if 'pid' in sched_itemes:
			if 'iowait' in sched_itemes:
				if sched_itemes['iowait'] == '1':
					sched_itemes['tag'] = TAG_UNINTERUPTIBLE_SLEEP_IO
				else:
					sched_itemes['tag'] = TAG_UNINTERUPTIBLE_SLEEP
			else:
				sched_itemes['tag'] = TAG_UNINTERUPTIBLE_SLEEP
			self.update_sched_time(sched_itemes, int(sched_itemes['pid']))


	def run(self):
		type_filters = {
			TRACE_MARK : self.trace_mark_func,
			SCHED_SWITCH : self.sched_switch_func,
			SCHED_WAKEUP : self.sched_wakeup_func,
			SCHED_BLOCKED_REASON : self.sched_blocked_reason,
			CPU_FREQUENCY_LIMITS : self.correct_func,
			CPU_IDLE : self.correct_func,
		}

		if len(self.result_times) > 0:
			del(self.result_times)
			self.result_times = dict()
			
		self.col = list()
		#self.col.append('pid')
		for trace_mark_filter in self.trace_mark_filters:
			if 'SEPERATE' in self.trace_mark_filters[trace_mark_filter]:
				for idx in self.trace_mark_filters[trace_mark_filter]['SEPERATE']:
					self.col.append('{} #{}'.format(trace_mark_filter, idx))
			else:
				self.col.append(trace_mark_filter)

		for line in self.raw_data:
			for type_filter in type_filters:
				if type_filter in line:
					type_filters[type_filter](line)

		Max = 0
		self.MaxPid = 0
		for pid in self.result_times:
			if len(self.result_times[pid]) > Max:
				Max = len(self.result_times[pid])
				self.MaxPid = pid

			if 'launching' in self.result_times[pid]:
				self.system_server_pid = pid

##################################################################################################################################################################
#	DEFINE FUNCTIONS FOR DATAFRAME
##################################################################################################################################################################
	
	def get_marking_time(self, dtype='gap'):
		df = DataFrame(columns=self.col + ['pid'])

		for pid in self.result_times:
			row_data = dict()
			row_data['pid'] = int(pid)

			for title in self.result_times[pid]:
				if 'SEPERATE' in self.trace_mark_filters[title]:
					for filter_idx in self.trace_mark_filters[title]['SEPERATE']:
						if len(self.result_times[pid][title]) > filter_idx:
							if dtype == 'gap':
								row_data['{} #{}'.format(title, filter_idx)] = self.result_times[pid][title][filter_idx]['time']
							elif dtype == 'start':
								row_data['{} #{}'.format(title, filter_idx)] = self.result_times[pid][title][filter_idx]['start_time']	
							elif dtype == 'end':
								row_data['{} #{}'.format(title, filter_idx)] = self.result_times[pid][title][filter_idx]['end_time']					
				else:
					total_time = 0
					for time in self.result_times[pid][title]:
						if dtype == 'gap' and 'time' in time :
							total_time += time['time']
						elif dtype == 'start' and 'start_time' in time :
							total_time = time['start_time']	
						elif dtype == 'end' and 'end_time' in time :
							total_time = time['end_time']	
					row_data[title] = total_time

			df = df.append(row_data, ignore_index=True)
		return df.set_index('pid')

	def get(self, index, pid=0):
		if index in self.result_cores.keys():
			df = DataFrame.from_dict(self.result_cores[index])
			#display(df)
			return df

		df = DataFrame(columns=self.col, index=index)

		if pid == 0:
			MaxPid = self.MaxPid
		else:
			MaxPid = pid

		for title in self.result_times[MaxPid]:
			if 'SEPERATE' in self.trace_mark_filters[title]:
				for filter_idx in self.trace_mark_filters[title]['SEPERATE']:
					if len(self.result_times[MaxPid][title]) > filter_idx:
						df['{} #{}'.format(title, filter_idx)] = Series(hierarchy.get(self.result_times[MaxPid][title], index, num=filter_idx), index=index)
			else:
				df[title] = Series(hierarchy.get(self.result_times[MaxPid][title], index), index=index)

		return df

	def get_rawdata(self, index, pid=0):
		result = dict()

		if pid == 0:
			MaxPid = self.MaxPid
		else:
			MaxPid = pid

		for title in self.result_times[MaxPid]:
			if 'SEPERATE' in self.trace_mark_filters[title]:
				for filter_idx in self.trace_mark_filters[title]['SEPERATE']:
					if len(self.result_times[MaxPid][title]) > filter_idx:
						result['{} #{}'.format(title, filter_idx)] = hierarchy.get_rawdata(self.result_times[MaxPid][title], index, num=filter_idx)
			else:
				result[title] = hierarchy.get_rawdata(self.result_times[MaxPid][title], index)

		return result

	def unint_sleep(self, pid=0):
		index_data = list()

		if pid == 0:
			MaxPid = self.MaxPid
		else:
			MaxPid = pid

		for title in self.result_times[MaxPid]:
			if 'SEPERATE' in self.trace_mark_filters[title]:
				for filter_idx in self.trace_mark_filters[title]['SEPERATE']:
					if len(self.result_times[MaxPid][title]) > filter_idx:
						element = hierarchy.unint_sleep(self.result_times[MaxPid][title], num=filter_idx)
						index_data += element 
			else:
				element = hierarchy.unint_sleep(self.result_times[MaxPid][title])
				index_data += element 
		return index_data
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
#	DEFINE CLASS FOR SYSTRACE_PARSER
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################

class systrace_parser:
	def __init__(self, trace_mark_filters, file_names, title):
		self.trace_mark_filters = trace_mark_filters
		self.parsers_of_testing = list()
		self.title = title

		for file_name in file_names:
			try:
				file = open(file_name)
				file_lines = file.readlines()
				file.close()

				#print("Reading {} file is completed with {} lines\n".format(file_name, len(file_lines)))
			except e:
				print(e)
			file.close()

			#systrace_parser = parser_range(trace_mark_filters, file_lines, 0)
			self.parsers_of_testing += [parser_range(trace_mark_filters, file_lines, file_name)]

	def run(self):
		for parser in self.parsers_of_testing:
			parser.run()
			print("Parsing {} - {} lines are Ok".format(parser.title.split('/')[-1], len(parser.raw_data)))

	def get_file_name(self):
		return parser.file_name

	def get_marking_time(self, dtype='gap'):
		list_of_dataframe = list()
		for parser in self.parsers_of_testing:
			list_of_dataframe.append(parser.get_marking_time(dtype))
		return list_of_dataframe

	def get(self, index, func='avg', pids=[]):
		try:
			del(df)
		except:
			pass

		index_of_pids = 0
		for parser in self.parsers_of_testing:
			pid = 0
			if index_of_pids < len(pids):
				pid = pids[index_of_pids]
				index_of_pids += 1

			try:
				if func == 'array':
					df.append(parser.get(index, pid=pid))
				else:
					df += parser.get(index, pid=pid)
			except:
				if func == 'array':
					df = list()
					df.append(parser.get(index, pid=pid))
				else:
					df = parser.get(index, pid=pid)			

		if func == 'avg' :
			df /= len(self.parsers_of_testing)
		return df

	@staticmethod
	def process_state():
		return ['time', TAG_RUNNING, TAG_RUNNABLE, TAG_SLEEPING, TAG_UNINTERUPTIBLE_SLEEP, TAG_UNINTERUPTIBLE_SLEEP_IO]

	def cores(self):
		return ['core{}'.format(idx) for idx in range(8)] 

	def unint_sleep(self):
		index_data = list()
		for parser in self.parsers_of_testing:
			elements = parser.unint_sleep()
			for element in elements:
				if not element in index_data:
					index_data += [element]
		return index_data
