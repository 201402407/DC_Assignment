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
frame, seq = 0, 0

def SEQ_ACK_toBytes(seq_int, ack_int): # SEQ, ACK를 하나의 바이트로 합치는 함수.
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
	
	if frame == 0 and seq == 0: # 맨 처음 파일 정보 받기 위한 조건. 재전송 받아도 들어올 수 있는 조건.
		if data[0:20] == check: # 무결성 검사 통과하면.
			temp2 = temp - 8
			data_filename = data[21:temp2].decode()
			data_max_size = struct.unpack("!Q", data[temp2:])[0]
			data_filepath = "./receiveFolder/" + data_filename
			print("File Name = " + data_filename)
			print("File size = " , data_max_size)
			print("received file path = " + data_filepath)

			send_data = SEQ_ACK_toBytes(seq, seq)
			server_sock.sendto(send_data, addr) # 전송
			receive_file = open(data_filepath, "wb")			
			frame += 1
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
			if data_size == data_max_size: # 해당 파일 데이터를 전부 받은 경우.
				print("100% received end.")
				break
				
			if frame % 27 == 0 and frame != 0:
				print("wait for 2...")
				time.sleep(2)
			
			if data[0:20] == check: # 무결성검사 통과
				seq_ack_data = struct.unpack(">B", data[20:21])[0] # int
			
				temp = (bin(seq_ack_data)).replace("0b", "") # int -> str(binary) -> "0b" delete.
				temp = temp.zfill(8) # 8비트 중 남은 앞 공간을 0으로 채우기.
				seq_data = int(temp[0:4], 2) # seq int
				ack_data = int(temp[4:8], 2) # ack int

				if seq != seq_data: # 현재 전송받은 데이터의 seq와 받아야 할 seq가 다른 경우. = discard
					print("Data discarded.")
					send_data = SEQ_ACK_toBytes(seq, seq)
					server_sock.sendto(send_data, addr) # 전송. 이전 받은 프레임의 SEQ, ACK 전송 
					continue

				else: # 정상적인 경우.
					receive_file.write(data[21:])
					data_size += len(data[21:])
					percent = round((int(data_size) / (int(data_max_size)) * 100.00), 3)
					print("(current size / total size) = " + str(data_size) + "/" + str(data_max_size) + " , " + str(percent) + " %")
					server_sock.sendto(data[20:21], addr) # 전송.
					seq = (seq + 1) % 8
					frame += 1
					if data_size == data_max_size: # 해당 파일 데이터를 전부 받은 경우.
						print("100% received end.")
						break
					continue
			else: # NAK 발생 시
				print("Data corrupted! NAK send. frame : ", frame, "seq : ",seq)
				ack = 15 # = 1111
				send_data = SEQ_ACK_toBytes(seq, ack) # seq는 다시 받아야 할 현재 프레임 번호. ack는 nak으로 바꿔 전송.
				server_sock.sendto(send_data, addr) # 전송
				continue
			
		except Exception as e:
			print(e)
	
print("complete!" + '\n')
print("File Receive End.")
receive_file.close()
