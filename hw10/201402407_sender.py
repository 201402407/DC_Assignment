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
nowFrame, lastFrame, seq, check = 0, 3, 0, 0

def SEQ_ACK_toBytes(seq_int, ack_int):
	seq_int = seq_int << 4
	ack_int = ack_int & 0b1111
	temp = ((seq_int|ack_int).to_bytes(1, "big"))
	return temp

if os.path.isfile(filename):
	while True:
		if nowFrame == 0 and seq == 0:
			sha1 = hashlib.sha1() # 해쉬화 선언
			file_corrent_size = 0
			file_size = os.path.getsize(filename)
			filename = filename.encode()
			header = filename
			header += file_size.to_bytes(8, byteorder = "big")
			seq_ack = SEQ_ACK_toBytes(seq, seq) # SEQ, ACK 각각 4비트를 1바이트로 합침.
			
			header = seq_ack + header # seq,ack + header 해쉬화
			sha1.update(header) # 해쉬화
			temp = sha1.digest() # byte 변환
	
			temp = temp + header # checksum + seq,ack + fileinfo
			print("Send File Info(file Name, file Size, seqNum) to Server...")
			clnt_sock.settimeout(1) # Timeout

			clnt_sock.sendto(temp, (serverIP, serverPort)) # 전송.
			seq += 1

		with open(filename, 'rb') as sendfile:
			try:
				print("Start File send")
				data = sendfile.read(1024)
			
				while data:

					file_corrent_size += len(data)
					percent = round((int(file_corrent_size) / (int(file_size)) * 100.00), 3)
					print("(current size / total size) = " + str(file_corrent_size) + "/" + str(file_size) + " , " + str(percent) + " %")
					
					seq_ack = SEQ_ACK_toBytes(seq % 8, seq % 8)
					Checksum = seq_ack + data # byte
					sha1 = hashlib.sha1() # 해쉬화 정의
					sha1.update(Checksum)
					Checksum = sha1.digest() # byte
					
					send_data = Checksum + seq_ack + data # byte
									
					if seq % 20 == 0 and check != 2:
						send_data = data
					if seq == nowFrame: # window size 첫 프레임 전송을 시작으로 timeout setting.
						clnt_sock.settimeout(1)
						clnt_sock.sendto(send_data, (serverIP, serverPort)) # 전송
					else: # 첫 프레임이 아닐 때
						clnt_sock.sendto(send_data, (serverIP, serverPort)) # 전송
					
					
					if seq == lastFrame: # window size(4번)만큼의 전송을 했다면. 또는 연속 프레임 전송이 아닐 때.
						try:
							while True:
								seq_ack = clnt_sock.recvfrom(1) # 수신받는다.
							
								seq_ack_data = struct.unpack(">B", seq_ack[0])[0]
								temp = (bin(seq_ack_data
)).replace("0b", "")
								temp = temp.zfill(8)
								seq_data = int(temp[0:4], 2)
								ack_data = int(temp[4:8], 2)

								if nowFrame % 8 != seq_data:
									print("Data discarded!!!")
									continue
								else:
									break
								
							if ack_data == 15: # NAK 전송 받았을 시.
								print("*** NAK received!!! ***")
								check = 2 # NAK type으로 설정.
								sendfile.seek(-((1024*(seq - nowFrame)) + len(data)), 1) # 1024 * window size byte 뒤로 간다.
								file_corrent_size = file_corrent_size - ((1024 * (seq - nowFrame)) + len(data))
								seq = nowFrame # 다시 보내야 할 프레임으로 seq를 맞춘다.
								percent = round((int(file_corrent_size) / (int(file_size)) * 100.00), 3)
								print("여기서부터 전송 : (current size / total size) = " + str(file_corrent_size) + "/" + str(file_size) + " , " + str(percent) + " %")
								data = sendfile.read(1024) # 파일 읽기.
								continue
									
							 # 정상 프레임을 전송 받았을 시. 이전 frame들은 전부 무사히 전송받은걸로 취급.
							check = 0 # normal type으로 설정.
							nowFrame += 1
							lastFrame += 1
							seq += 1 # window size 첫 프레임, 끝 프레임, 파일 전송한 프레임 전부 1씩 더한다. (한 칸 옆으로 이동)
							data = sendfile.read(1024) 
							clnt_sock.settimeout(1) # ??

						except socket.timeout: # Timeout
							print("*** Timeout !!! ***")
							print("윈도우 첫 프레임 : ", nowFrame)

							check = 1 # Timeout type으로 설정.
							sendfile.seek(-((1024*(seq - nowFrame)) + len(data)), 1) # 1024 * window size byte 뒤로 간다. + 맨 끝 예외 처리.
							file_corrent_size = file_corrent_size - ((1024 * (seq - nowFrame)) + len(data))
							seq = nowFrame # 다시 보내야 할 프레임으로 seq를 맞춘다.
							percent = round((int(file_corrent_size) / (int(file_size)) * 100.00), 3)
							print("여기서부터 전송 : (current size / total size) = " + str(file_corrent_size) + "/" + str(file_size) + " , " + str(percent) + " %")

							data = sendfile.read(1024) # 파일 읽기.
							continue
					else: # window frame 연속 전송 중 첫 번째 프레임 제외한 나머지 프레임 수신.
						if check == 2: # NAK 이후 수신하는 패킷은 전부 discard한다.
							try:
								clnt_sock.settimeout(1) # 이 시간동안 수신을 안받으면 더이상 discard한 데이터가 없는 것으로 간주.
								seq_ack = clnt_sock.recvfrom(1) # 수신받는다.	
								print("Data discarded!!!")
							except socket.timeout:
								print("checkout")
						seq += 1
						data = sendfile.read(1024)
						continue
			except 	Exception as e:
				print(e)		
		break
else:
	print("입력하신 파일이 존재하지 않습니다.", '\n')
print("File Send End.")
sendfile.close()


