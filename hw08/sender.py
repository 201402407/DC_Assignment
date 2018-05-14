import socket
import os
import struct
import hashlib
import time

serverIP = '127.0.0.1'
serverPort = 3333

print("Sender Socket open..")
print("Receiver IP = ", serverIP)
print("Receiver Port = ", serverPort)

clnt_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

filename = input("Input File Name : ")
frame = 0
seq = 0
if os.path.isfile(filename):

	if frame == 0:
		sha1 = hashlib.sha1() # 해쉬화
		file_corrent_size = 0
		file_size = os.path.getsize(filename)
		filename = filename.encode()
		header = filename
		header += file_size.to_bytes(8, byteorder = "big")
		seq = seq.to_bytes(1, byteorder = "big")
		header = seq + header # seq + header 해쉬화
		sha1.update(header) # 해쉬화
		temp = sha1.digest() # byte 변환

		temp = temp + header # checksum + seq + fileinfo
		print("Send File Info(file Name, file Size, seqNum) to Server...")
		clnt_sock.settimeout(1) # Timeout
		clnt_sock.sendto(temp, (serverIP, serverPort)) # 전송
		while True:
			try:
						
				temp2 = clnt_sock.recvfrom(1) # tuple , 수신
				seq = struct.unpack("!B", seq)[0] # int
				ACK = struct.unpack("!B", temp2[0])[0] # int
				if (seq + 1) % 2 == ACK:
					seq += 1
					frame += 1
					break
				if ACK == 2: # NAK
					print("Received NAK - Retransmit!")
					print("Retransmission : (current size / total size) = " + str(file_corrent_size) + "/" + str(file_size) + " , " + str(percent) + " %")
					clnt_sock.sendto(temp, (serverIP, serverPort)) # 전송, 시간은 계속 흐르게 해야 하므로.
					continue
			except socket.timeout:
				print("*** TimeOut!! ***")
				clnt_sock.settimeout(1)
				clnt_sock.sendto(temp, (serverIP, serverPort)) # 전송, timeout이므로 시간도 다시 설정해야 한다.
				continue
		
	with open(filename, 'rb') as sendfile:
		try:
			print("Start File send")
			data = sendfile.read(1024)
		
			while data:
					
				file_corrent_size += len(data)
				percent = round((int(file_corrent_size) / (int(file_size)) * 100.00), 3)
				print("(current size / total size) = " + str(file_corrent_size) + "/" + str(file_size) + " , " + str(percent) + " %")
				
				SEQ = seq.to_bytes(1, byteorder = "big") # byte
				Checksum = SEQ + data # byte
				sha1 = hashlib.sha1()
				sha1.update(Checksum)
				Checksum = sha1.digest() # byte
				
				send_data = Checksum + SEQ + data # byte
				clnt_sock.settimeout(1)
				if frame % 44 == 0:
					clnt_sock.sendto(data, (serverIP, serverPort)) # 데이터 손실 체크를 위한 임의의 데이터 전송
				else:
					clnt_sock.sendto(send_data, (serverIP, serverPort)) # 전송
				
				while True:
					try:	
						ack = clnt_sock.recvfrom(1) # 수신
						ACK = struct.unpack("!B", ack[0])[0] # int
						seq = struct.unpack("!B", SEQ)[0] # int
						if (seq + 1) % 2 == ACK:
							seq = (seq + 1) % 2
							frame += 1
							data = sendfile.read(1024) 
							break
						if seq == ACK: # 이전 프레임의 ACK인 경우
							print("ACK discarded.")
							continue
						if ACK == 2: # NAK
							print("Received NAK - Retransmit!")
							print("Retransmission : (current size / total size) = " + str(file_corrent_size) + "/" + str(file_size) + " , " + str(percent) + " %")
							clnt_sock.sendto(send_data, (serverIP, serverPort))
							continue
					except socket.timeout:
						print("*** TimeOut!! ***")
						clnt_sock.settimeout(1)
						print("Retransmission : (current size / total size) = " + str(file_corrent_size) + "/" + str(file_size) + " , " + str(percent) + " %")
						clnt_sock.sendto(send_data, (serverIP, serverPort))
						continue
		except Exception as e:
			print(e)		
else:
	print("입력하신 파일이 존재하지 않습니다.", '\n')
print("frame : " , frame)
print("File Send End.")
sendfile.close()


