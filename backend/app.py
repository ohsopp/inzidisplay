import json
import queue
import socket
import threading
from flask import Flask, Response, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

client_queues = []
client_queues_lock = threading.Lock()
udp_thread = None
listening = False
udp_state = None  # {"ip": str, "port": int} when connected


def broadcast(event: str, data: dict):
    """모든 연결된 SSE 클라이언트에 이벤트 전달"""
    msg = {"event": event, "data": data}
    with client_queues_lock:
        for q in list(client_queues):
            try:
                q.put_nowait(msg)
            except queue.Full:
                pass


def udp_listener(ip: str, port: int):
    """UDP 메시지를 수신하고 모든 SSE 클라이언트에 전달"""
    global listening, udp_state
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((ip, port))
        listening = True
        udp_state = {"ip": ip, "port": port}

        broadcast("udp_connected", {"ip": ip, "port": port})

        while listening:
            try:
                sock.settimeout(1.0)
                data, addr = sock.recvfrom(1024)
                xfmt = "".join(f"x{b:02x}" for b in data)
                try:
                    text = data.decode("utf-8")
                    payload = xfmt if (not text or "\x00" in text or not text.isprintable()) else text
                except UnicodeDecodeError:
                    payload = xfmt
                broadcast("udp_data", {
                    "payload": payload,
                    "raw": data.hex(),
                    "addr": f"{addr[0]}:{addr[1]}",
                })
            except socket.timeout:
                continue
            except OSError:
                break
        sock.close()
    except OSError as e:
        if e.errno == 49:  # EADDRNOTAVAIL
            broadcast("udp_error", {
                "message": "해당 IP를 사용할 수 없습니다. 바인딩 IP는 이 PC의 IP이거나 0.0.0.0(모든 인터페이스)이어야 합니다. PLC IP가 아닙니다."
            })
        else:
            broadcast("udp_error", {"message": str(e)})
    except Exception as e:
        broadcast("udp_error", {"message": str(e)})
    finally:
        listening = False
        udp_state = None
        broadcast("udp_disconnected", {})


def sse_stream(client_queue):
    """SSE 스트림 생성 - 각 클라이언트 전용 큐 사용"""
    try:
        while True:
            try:
                msg = client_queue.get(timeout=30)
                yield f"event: {msg['event']}\ndata: {json.dumps(msg['data'])}\n\n"
            except queue.Empty:
                yield ": heartbeat\n\n"
    finally:
        with client_queues_lock:
            if client_queue in client_queues:
                client_queues.remove(client_queue)


@app.route("/api/events")
def events():
    """SSE 엔드포인트 - 각 연결마다 별도 큐로 브로드캐스트"""
    client_queue = queue.Queue()
    with client_queues_lock:
        client_queues.append(client_queue)
        # 이미 UDP가 실행 중이면 새 클라이언트에 현재 상태 전달
        if udp_state:
            try:
                client_queue.put_nowait({"event": "udp_connected", "data": udp_state})
            except queue.Full:
                pass
    return Response(
        sse_stream(client_queue),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/start_udp", methods=["POST"])
def start_udp():
    global udp_thread
    data = request.get_json() or {}
    ip = data.get("ip", "0.0.0.0")
    port = int(data.get("port", 5212))

    if udp_thread and udp_thread.is_alive():
        return {"error": "이미 UDP 리스너가 실행 중입니다."}, 400

    udp_thread = threading.Thread(target=udp_listener, args=(ip, port))
    udp_thread.daemon = True
    udp_thread.start()

    return {"ok": True}


@app.route("/api/stop_udp", methods=["POST"])
def stop_udp():
    global listening
    listening = False
    return {"ok": True}


@app.route("/api/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6005, debug=True, use_reloader=False, threaded=True)
