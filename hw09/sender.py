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
frame, seq, ack = -1, 0, 0

def SEQ_ACK_toBytes(seq_int, ack_int):
	seq_int = seq_int << 4
	ack_int = ack_int & 0b1111
	

	temp = ((seq_int|ack_int).to_bytes(1, "big"))
	return temp

if os.path.isfile(filename):
	while True:
		if frame == -1 and seq == 0:
			sha1 = hashlib.sha1() # 해쉬화 선언
			file_corrent_size = 0
			file_size = os.path.getsize(filename)
			filename = filename.encode()
			header = filename
			header += file_size.to_bytes(8, byteorder = "big")
			seq_ack = SEQ_ACK_toBytes(seq, ack) # SEQ, ACK 각각 4비트를 1바이트로 합침.
			
			header = seq_ack + header # seq,ack + header 해쉬화
			sha1.update(header) # 해쉬화
			temp = sha1.digest() # byte 변환
	
			temp = temp + header # checksum + seq,ack + fileinfo
			print("Send File Info(file Name, file Size, seqNum) to Server...")
	#		clnt_sock.settimeout(1) # Timeout

			clnt_sock.sendto(temp, (serverIP, serverPort)) # 전송.
			seq += 1
			ack += 1

		with open(filename, 'rb') as sendfile:
			try:
				print("Start File send")
				data = sendfile.read(1024)
			
				while data:

					file_corrent_size += len(data)
					percent = round((int(file_corrent_size) / (int(file_size)) * 100.00), 3)
					print("(current size / total size) = " + str(file_corrent_size) + "/" + str(file_size) + " , " + str(percent) + " %")
					
					seq_ack = SEQ_ACK_toBytes(seq, ack)
					Checksum = seq_ack + data # byte
					sha1 = hashlib.sha1() # 해쉬화 정의
					sha1.update(Checksum)
					Checksum = sha1.digest() # byte
					
					send_data = Checksum + seq_ack + data # byte
				#	clnt_sock.settimeout(1)
				#	if frame % 44 == 0:
				#		clnt_sock.sendto(data, (serverIP, serverPort)) # 데이터 손실 체크를 위한 임의의 데이터 전송
				#	else:
					clnt_sock.sendto(send_data, (serverIP, serverPort)) # 전송
					a = frame + 4

					if a % 8 == seq: # 만약 window size만큼 전송을 했다면
						seq_ack = clnt_sock.recvfrom(1) # 수신받는다.
						print("window control 끝 프레임까지 전송!")
						seq_ack_data = struct.unpack(">B", seq_ack[0])[0]
						temp = (bin(seq_ack_data)).replace("0b", "")
						temp = temp.zfill(8)
						seq_data = int(temp[0:4], 2)
						ack_data = int(temp[4:8], 2)
				
						if temp[4:8] == "1111": # NAK 전송 받았을 시.
							print("NAK error!")
							if frame == -1:
								break
							else:
								print("aaa")
								break
						 # 정상 프레임을 전송 받았을 시. 이전 frame들은 전부 무사히 전송받은걸로 취급.
						frame += 4
						seq = (seq_data + 1) % 8
						ack = (ack_data + 1) % 8
						data = sendfile.read(1024)
						continue
					else: # 아직 window size만큼 전송을 받지 못했다면
						seq = (seq + 1) % 8
						ack = (ack + 1) % 8
						data = sendfile.read(1024)
						continue
	
			except 	Exception as e:
				print(e)		
		break
else:
	print("입력하신 파일이 존재하지 않습니다.", '\n')
print("File Send End.")
sendfile.close()


