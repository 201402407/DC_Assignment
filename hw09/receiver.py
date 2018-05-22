import socket
import struct
import hashlib
import os
import time

ip_address = '127.0.0.1'
port_number = 3333

server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # 패킷 열린 채로 닫힘 방지
server_sock.bind((ip_address, port_number))
print("Server socket open...")

print("Send file info ACK..")

data_size = 0
data_max_size = 0
frame, seq = -1, 0

def SEQ_ACK_NAK(seq_int, ack_int):
	seq_int = seq_int << 4
	ack_int = ack_int & 0b1111
	temp = ((seq_int|ack_int).to_bytes(1, "big"))
	return temp

while True:	
	data,addr = server_sock.recvfrom(1045) # 수신
	
	if not data: # 만약 데이터에 값이 없으면 종료
		break
	temp = len(data)
	sha1 = hashlib.sha1()
	sha1.update(data[20:])
	check = sha1.digest() # 암호화
	
	if frame == -1 and seq == 0: # 맨 처음 파일 정보 받기 위한 조건. 재전송 받아도 들어올 수 있는 조건.
		if data[0:20] == check: # 무결성 검사 통과하면.
			temp2 = temp - 8
			data_filename = data[21:temp2].decode()
			data_max_size = struct.unpack("!Q", data[temp2:])[0]
			data_filepath = "./receiveFolder/" + data_filename
			print("File Name = " + data_filename)
			print("File size = " , data_max_size)
			print("received file path = " + data_filepath)
			
			receive_file = open(data_filepath, "wb")			
			seq += 1
			continue

		if data[0:20] != check: # 중간에 데이터가 손상되었을 시. NAK 전송
			print("Data corrupted!!")
			
			ack = 0b1111
			seq = seq << 4
			send_data = ((seq|ack).to_bytes(1, "big"))
			server_sock.sendto(send_data, addr) # 전송
			continue
	
	else: # 파일 정보가 아닌 파일 데이터 전송 진행.
		try:
		#	if frame % 40 == 0:
		#		print("wait for 2...")
		#		time.sleep(2)
				
			if data[0:20] == check: # 무결성검사 통과
				seq_ack_data = struct.unpack(">B", data[20:21])[0] # int
			
				temp = (bin(seq_ack_data)).replace("0b", "") # int -> str(binary) -> "0b" delete.
				temp = temp.zfill(8) # 8비트 중 남은 앞 공간을 0으로 채우기.
				seq_data = int(temp[0:4], 2) # seq int
				ack_data = int(temp[4:8], 2) # ack int
				if seq != seq_data: # 현재 전송받은 데이터의 seq와 받아야 할 seq가 다른 경우. = discard
					print("Data discarded.")
					continue
				a = frame + 4 # 비교를 위한 임의의 변수
				if a % 8 == seq % 8: # window size만큼 한번에 데이터를 받으면
					print("4번의 데이터를 전송 받음 ! ")
					receive_file.write(data[21:])
					data_size += len(data[21:])
					percent = round((int(data_size) / (int(data_max_size)) * 100.00), 3)
					print("(current size / total size) = " + str(data_size) + "/" + str(data_max_size) + " , " + str(percent) + " %")
					server_sock.sendto(data[20:21], addr) # 전송. 맨 마지막의 seq,ack 전송
					seq = (seq + 1) % 8
					frame += 4
					if data_size == data_max_size:
						print("100% receive end")
						break
					continue
				else: # 아직 수신이 남은 경우. seq에 1을 더하고 continue.
					receive_file.write(data[21:])
					data_size += len(data[21:])
					percent = round((int(data_size) / (int(data_max_size)) * 100.00), 3)
					print("(current size / total size) = " + str(data_size) + "/" + str(data_max_size) + " , " + str(percent) + " %")
					seq = (seq + 1) % 8
					if data_size == data_max_size:
						break
					continue
			else: # NAK 발생 시
				print("Data corrupted! NAK send")
				ack = 0b1111
				seq = seq << 4
				send_data = ((seq|ack).to_bytes(1, "big"))
				server_sock.sendto(send_data, addr) # 전송
				continue
			
		except Exception as e:
			print(e)
	
print("complete!" + '\n')
print("File Receive End.")
receive_file.close()
