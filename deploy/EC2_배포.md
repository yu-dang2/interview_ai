# EC2 배포 절차

한이음 AWS 계정으로 로그인한 뒤, 위에서부터 순서대로 진행한다.
`<공인IP>` 는 인스턴스를 만들고 나면 나오는 값으로 바꿔 넣는다.

---

## 1. 인스턴스 생성 (AWS 콘솔)

| 항목 | 값 | 이유 |
|---|---|---|
| 리전 | 시드니 (ap-southeast-2) | 한이음 계정에서 이 리전만 쓸 수 있다 |
| AMI | Ubuntu Server 24.04 LTS (x86) | Docker 공식 저장소가 지원한다. 콘솔 목록에 22.04 일반판이 없다 |
| 인스턴스 타입 | t3.medium (2vCPU / 4GB) | t2.micro 는 빌드 중 메모리 부족으로 죽는다 |
| 스토리지 | 30 GiB gp3 | 이미지 3.1GB + 빌드 캐시 + 영상. 8GB 로는 부족하다 |
| 키 페어 | 새로 생성 → .pem 저장 | 다시 받을 수 없다 |

### 보안 그룹

| 유형 | 포트 | 소스 |
|---|---|---|
| SSH | 22 | 내 IP |
| 사용자 지정 TCP | 8080 | 0.0.0.0/0 |

8000·8501 은 열지 않는다. 프록시(8080)가 화면과 API 를 모두 받으므로 필요 없고,
열어두면 프록시를 우회하는 경로가 생긴다.

---

## 2. 접속

```bash
chmod 400 키파일.pem
ssh -i 키파일.pem ubuntu@<공인IP>
```

Windows PowerShell 에서 `chmod` 가 없으면 그냥 `ssh` 만 실행해도 되는 경우가 많다.
권한 오류가 나면 파일 속성 > 보안에서 본인 외 사용자를 제거한다.

---

## 3. Docker 설치

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

마지막 줄을 적용하려면 한 번 나갔다 다시 들어온다.

```bash
exit
ssh -i 키파일.pem ubuntu@<공인IP>
docker --version
```

---

## 4. 코드 받기

```bash
git clone https://github.com/Yejineeeee/interview_ai.git
cd interview_ai
git checkout develop
```

`feature/backend` 의 배포 설정이 develop 에 머지된 뒤에 받아야 한다.
아직이면 `git checkout feature/backend` 로 받는다.

---

## 5. .env 작성

```bash
nano .env
```

아래 내용을 붙여넣고 값을 채운다.

```
OPENAI_API_KEY=본인_키
SECRET_KEY=고정값_생성해서_넣기
LLM_MODEL=gpt-5-mini

# 배포 주소. 프록시가 화면과 API 를 모두 받으므로 /api 를 붙인다.
PUBLIC_API_BASE_URL=http://<공인IP>:8080/api
CORS_ORIGINS=http://<공인IP>:8080

ENVIRONMENT=production
```

`SECRET_KEY` 생성:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

`DATABASE_URL` 은 쓰지 않는다. compose 가 `db:3306` 으로 덮어쓴다.
`API_BASE_URL` 도 기본값(`http://api:8000`)이 맞으므로 생략한다.

---

## 6. 빌드와 기동

```bash
docker compose build
docker compose up -d
docker compose ps
```

첫 빌드는 20~40분 걸린다. mediapipe·opencv 설치가 대부분이다.
4개 서비스(db·api·web·proxy)가 모두 healthy 가 되어야 한다.

---

## 7. 직무 지식 인덱스 생성

```bash
docker compose exec api python scripts/build_knowledge_index.py
```

한 번만 하면 볼륨에 남는다. 카드(`data/job_knowledge_v2.json`)가 바뀔 때만 다시 한다.
안 하면 에러 없이 검색 결과가 비어서 나간다.

---

## 8. 확인

```bash
curl -s http://localhost:8080/api/health
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/
```

`healthy` 와 `200` 이 나오면 브라우저에서 연다.

```
http://<공인IP>:8080
```

회원가입 → 이력서·JD 등록 → 면접 시작 → 결과 리포트까지 한 바퀴 돈다.

---

## 9. HTTPS 적용

브라우저는 카메라와 마이크를 HTTPS 에서만 허용한다(localhost 는 예외).
http 로 띄우면 텍스트 면접만 되고 음성 답변·웹캠 녹화가 동작하지 않는다.

도메인은 sslip.io 를 쓴다. 한이음 계정으로는 Route 53 과 도메인 구입이 막혀 있다.
sslip.io 는 `15-134-182-6.sslip.io` 처럼 IP 의 점을 하이픈으로 바꾼 이름을 그대로
그 IP 로 해석해주므로 DNS 설정 없이 쓸 수 있다.

벤더가 권하는 CloudFront 는 쓰지 않았다. 오리진 응답 상한이 60초인데
리포트 생성이 실측 74~245초라 중도 종료가 끊긴다.

### 인증서 발급

80 포트가 비어 있어야 한다. 프록시가 8080 만 쓰는 상태에서 먼저 받는다.

```bash
sudo apt-get install -y certbot
sudo certbot certonly --standalone -d <IP를 하이픈으로>.sslip.io \
  --non-interactive --agree-tos --register-unsafely-without-email
```

### .env 수정

```
PUBLIC_API_BASE_URL=https://<IP를 하이픈으로>.sslip.io/api
CORS_ORIGINS=https://<IP를 하이픈으로>.sslip.io
```

### 기동

HTTPS 설정은 오버레이로 분리되어 있다. 로컬에는 인증서가 없어 기본 compose 에
넣으면 프록시가 뜨지 않기 때문이다.

```bash
docker compose -f docker-compose.yml -f docker-compose.https.yml up -d
```

`deploy/nginx.https.conf` 의 `ssl_certificate` 경로에 도메인이 박혀 있다.
Elastic IP 가 바뀌면 그 두 줄과 위 `.env` 두 줄을 같이 고치고 인증서를 다시 받아야 한다.

## 알아둘 것

### 인증서 자동 갱신은 실패한다

certbot 이 `standalone` 으로 발급했는데, 지금은 nginx 가 80 포트를 쓰고 있어
갱신이 포트 충돌로 실패한다.

```
Could not bind TCP port 80 because it is already in use
```

만료는 발급일 기준 90일이고 갱신은 30일 전부터 시도하므로, 그 전에 서버를 내릴
계획이면 그대로 둬도 된다. 계속 운영하려면 갱신 설정에 pre/post 훅을 넣어
갱신 동안 프록시를 잠깐 멈추거나, `webroot` 방식으로 바꿔야 한다.

### 로그 보기

```bash
docker compose logs -f api
docker compose logs --tail 100 web
```

### 코드를 고친 뒤 반영

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.https.yml up -d --build
```

볼륨은 유지되므로 회원·면접 결과·영상·진행 중이던 면접이 남는다.

설정 파일만 고쳤을 때는 `--force-recreate` 가 필요하다.
`nginx.conf` 와 `nginx.https.conf` 는 파일 하나를 통째로 마운트하는데,
`git pull` 이 파일을 교체하면 inode 가 바뀌어 컨테이너는 옛 파일을 계속 본다.

```bash
docker compose -f docker-compose.yml -f docker-compose.https.yml up -d --force-recreate proxy
```

`.env` 를 고쳤을 때도 같다. 해당 서비스를 다시 만들어야 환경변수가 반영된다.

### 인스턴스를 껐다 켜면 공인 IP 가 바뀐다

탄력적 IP(Elastic IP)를 붙이면 고정된다. 붙이지 않으면 재시작할 때마다
`.env` 의 두 줄을 고치고 `docker compose up -d` 를 다시 해야 한다.
