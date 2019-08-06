import numpy as np
from pandas import Series, DataFrame

TRACE_MARK = 'tracing_mark_write:'
SCHED_SWITCH = 'sched_switch:'
SCHED_WAKEUP = 'sched_wakeup:'
SCHED_BLOCKED_REASON = 'sched_blocked_reason:'

TAG_RUNNING = 'RUNNING'
TAG_RUNNABLE = 'RUNNABLE'
TAG_SLEEPING = 'SLEEPING'
TAG_UNINTERUPTIBLE_SLEEP = 'UNINTERUPTIBLE_SLEEP'
TAG_UNINTERUPTIBLE_SLEEP_IO = 'UNINTERUPTIBLE_SLEEP(I/O)'

class hierarchy:

	@staticmethod
	def open(current_time):
		hnd = dict()
		hnd['time'] = current_time
		hnd['sched_time'] = current_time
		hnd['on_process'] = True
		return hnd

	@staticmethod
	def close(hnd, current_time):
		hnd['time'] = current_time - hnd['time']
		hnd['on_process'] = False
		hnd[TAG_RUNNING] = hnd.get(TAG_RUNNING, 0) + (current_time - hnd['sched_time'])

	@staticmethod
	def set(hnd, set_data):
		hnd = hnd[-1]
		if 'on_process' in hnd and hnd['on_process']:
			######## Update process's state
			tag = set_data['tag']
			if tag == TAG_UNINTERUPTIBLE_SLEEP or tag == TAG_UNINTERUPTIBLE_SLEEP_IO:
				hnd['process_state'] = tag
			else:
				if 'process_state' in hnd and len(hnd['process_state']) > 0:
					tag = hnd['process_state']
					hnd['process_state'] = ''
				######## Update processing time
				hnd[tag] = hnd.get(tag, 0) + (set_data['time'] - hnd['sched_time'])
				hnd['sched_time'] = set_data['time']
				######## Update core number
				hnd['core'] = hnd.get('core', [0] * 8)  #conf["MAX_CORE_NUM"]
				if set_data['core'] < 8:  #conf["MAX_CORE_NUM"]:
					hnd['core'][set_data['core']] += 1

	@staticmethod
	def get_from_index(hnd, index):
		#print(index + '/' + index[:4])
		if index[:4] == 'core':
			core_num = int(index[-1])
			if core_num > len(hnd['core']):
				return 0
			else:
				return hnd['core'][core_num]
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

class parser_range:

	def __init__(self, trace_mark_filters, raw_data, start_line):
		self.trace_mark_filters = trace_mark_filters
		self.raw_data = raw_data
		self.start_line = start_line
		self.result_times = dict()   # Storing the time data.
		self.trace_mark_traversal = dict() # Storing the systrace tag's context to check end of it.

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
				result['pid'] = int(trace_mark[0][24:29].strip())
		except:
			pass

		try:
			if not 'pid' in result:
				result['pid'] = int(trace_mark[0][17:22].strip())
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
			elif trace_mark['type'] == 'E' and len(self.trace_mark_traversal[trace_mark['pid']]) > 0:
				trace_mark['context'] = self.trace_mark_traversal[trace_mark['pid']][-1]
				self.trace_mark_traversal[trace_mark['pid']] = self.trace_mark_traversal[trace_mark['pid']][0 : -1]

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
						#if '1250' in str:
						#    print(self.result_times)
				except:
					#if '1250' in str:
					#    print(str)
					#    print(trace_mark)
					pass
				#if 'launching:' in str:
				#    print(str)
				#    print(trace_mark)
		#    else:
		#        print(str)
		#        print(trace_mark)


	def parser_sched(self, str):
		result = dict()
		sched_items = str.split(' ')
		for sched_item in sched_items:
			if '=' in sched_item:
				sched_item = sched_item.split('=')
				result[sched_item[0]] = sched_item[1]

		sched_marks = str.split(': sched_')
		sched_marks = sched_marks[0].split(' ')
		result['time'] = float(sched_marks[-1])
		for sched_mark in sched_marks:
			if '[' in sched_mark and ']' in sched_mark:
				result['core'] = int(sched_mark.strip('[]'))
				break
		return result

	def update_sched_time(self, sched_itemes, pid):
		if pid in self.result_times:
			for trace_mark_filter in self.result_times[pid]:
				hierarchy.set(self.result_times[pid][trace_mark_filter], sched_itemes)

##################################################################################################################################################################
#	DEFINE FUNCTIONS FOR TRACE PARSER
##################################################################################################################################################################

	def sched_switch_func(self, str):
		sched_itemes = self.parser_sched(str)
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

##################################################################################################################################################################
#	DEFINE FUNCTIONS FOR DATAFRAME
##################################################################################################################################################################

	def get_marking_time(self):
		df = DataFrame(columns=self.col + ['pid'])

		Max = 0
		self.MaxPid = 0
		for pid in self.result_times:
			row_data = dict()
			row_data['pid'] = int(pid)

			if len(self.result_times[pid]) > Max:
				Max = len(self.result_times[pid])
				self.MaxPid = pid

			for title in self.result_times[pid]:
				if 'SEPERATE' in self.trace_mark_filters[title]:
					for filter_idx in self.trace_mark_filters[title]['SEPERATE']:
						if len(self.result_times[pid][title]) > filter_idx:
							row_data['{} #{}'.format(title, filter_idx)] = self.result_times[pid][title][filter_idx]['time'] #* 1000
				else:
					total_time = 0
					for time in self.result_times[pid][title]:
						total_time += time['time']
					row_data[title] = total_time #* 1000

			df = df.append(row_data, ignore_index=True)
		return df.set_index('pid')

	def get(self, index, pid=0):
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

	def process_state(self):
		return ['time', TAG_RUNNING, TAG_RUNNABLE, TAG_SLEEPING, TAG_UNINTERUPTIBLE_SLEEP, TAG_UNINTERUPTIBLE_SLEEP_IO]

	def cores(self):
		return ['core{}'.format(idx) for idx in range(8)] 

class systrace_parser:
	def __init__(self, trace_mark_filters, file_names):
		self.trace_mark_filters = trace_mark_filters
		self.parsers_of_testing = list()
		for file_name in file_names:
			try:
				file = open(file_name)
				file_lines = file.readlines()
				file.close()

				print("Reading {} file is completed with {} lines".format(file_name, len(file_lines)))
			except e:
				print(e)
			file.close()

			#systrace_parser = parser_range(trace_mark_filters, file_lines, 0)
			self.parsers_of_testing += [parser_range(trace_mark_filters, file_lines, 0)]

	def run(self):
		for parser in self.parsers_of_testing:
			parser.run()
