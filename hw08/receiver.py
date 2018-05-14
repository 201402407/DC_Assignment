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
ack = 0
frame = 0

while True:	
	data,addr = server_sock.recvfrom(1045) # 수신
	
	if not data: # 만약 데이터에 값이 없으면 종료
		break
	temp = len(data)
	sha1 = hashlib.sha1()
	sha1.update(data[20:])
	check = sha1.digest() # 암호화

	if data[0:20] == check: # 무결성 검사 통과하면
		temp2 = temp - 8
		data_filename = data[21:temp2].decode()
		data_max_size = struct.unpack("!Q", data[temp2:])[0]
		data_filepath = "./receiveFolder/" + data_filename
		print("File Name = " + data_filename)
		print("File size = " , data_max_size)
		print("received file path = " + data_filepath)
		
		receive_file = open(data_filepath, "wb")
		seq = struct.unpack("!B", data[20:21])[0] # int
		ack = (seq + 1) % 2
		ack = ack.to_bytes(1, byteorder = "big") # byte
		frame += 1
		server_sock.sendto(ack, (addr)) # 전송
		break
	if data[0:20] != check: # 중간에 데이터가 손상되었을 시
		ack = 2 # int
		ack = ack.to_bytes(1, byteorder = "big") # byte
		server_sock.sendto(ack, (addr)) # 전송
		continue
while True:
	
	try:
		sha1 = hashlib.sha1()
		temp = data # 이전 프레임 데이터와 비교하기 위한 임시 저장
		data, addr = server_sock.recvfrom(1045) # 수신
		sha1.update(data[20:])
		check = sha1.digest()
		if frame % 40 == 0:
			print("wait for 2...")
			time.sleep(2)
		if data == temp: # 이전 프레임의 데이터를 전송받았다면
			temp2 = struct.unpack("!B", ack)[0]
			if(temp2 != 2): # NAK인 경우에 대한 예외 처리. NAK이 아니었다면
				print("data discarded. previous ACK send.")
				server_sock.sendto(ack, addr) # 이전 ACK값 전송
				continue
		if data[0:20] == check:
		
			receive_file.write(data[21:])
			data_size += len(data[21:])
			
			percent = round((int(data_size) / (int(data_max_size)) * 100.00), 3)
			print("(current size / total size) = " + str(data_size) + "/" + str(data_max_size) + " , " + str(percent) + " %")

			seq = struct.unpack("!B", data[20:21])[0]
			ack = (seq + 1) % 2
			ack = ack.to_bytes(1, byteorder = "big")
			frame += 1
			server_sock.sendto(ack, addr) # 전송
			
			if data_size == data_max_size:
				break
		if data[0:20] != check:
			print("*** Packet corrupted!! *** - Send To Sender NAK(2)")
			ack = 2
			ack = ack.to_bytes(1, byteorder = "big")
			server_sock.sendto(ack, addr)
			continue
		
	except Exception as e:
		print(e)

print("complete!" + '\n')
print("File Receive End.")
receive_file.close()
