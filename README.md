# 2Beats

> 음악과 영상을 즐기는 새로운 방법 - 미디어 스트리밍 플랫폼

## 목차

- [프로젝트 소개](#프로젝트-소개)
- [주요 기능](#주요-기능)
- [기술 스택](#기술-스택)
- [시스템 아키텍처](#시스템-아키텍처)
- [설치 및 실행](#설치-및-실행)
- [데이터베이스 구조](#데이터베이스-구조)
- [API 문서](#api-문서)
- [배포](#배포)

## 프로젝트 소개

2Beats는 음악과 영상 콘텐츠를 업로드하고 스트리밍할 수 있는 미디어 플랫폼입니다.
사용자는 좋아하는 음악과 영상을 플레이리스트로 관리하고, 다른 사용자와 공유하며,
독특한 음악 월드컵 게임을 통해 자신만의 취향을 발견할 수 있습니다.

### 핵심 가치

- **간편한 미디어 관리**: 음악과 영상을 하나의 플랫폼에서 통합 관리
- **개인화된 경험**: 맞춤형 플레이리스트와 재생 기록 추적
- **소셜 기능**: 댓글과 좋아요를 통한 커뮤니티 형성
- **재미있는 발견**: 음악 월드컵을 통한 새로운 음악 발견

## 주요 기능

### 1. 미디어 관리

- **음악 스트리밍**
  - 다양한 장르의 음악 업로드 및 재생
  - 지원 장르: 발라드, 댄스, 힙합, R&B, 록, 팝, 인디, 트로트, 재즈, OST
  - 고품질 오디오 스트리밍
  - 재생 횟수 및 인기도 추적

- **영상 콘텐츠**
  - 뮤직비디오, 퍼포먼스, 라이브, 커버 등 다양한 영상 타입 지원
  - 자동 썸네일 생성
  - 조회수 및 재생 통계

### 2. 플레이리스트 시스템

- **음악 플레이리스트**
  - 개인 맞춤형 음악 폴더 생성
  - 드래그 앤 드롭으로 곡 순서 조정
  - 플레이리스트 공유 기능

- **영상 플레이리스트**
  - 영상 컬렉션 관리
  - 시리즈 재생 지원

### 3. 소셜 기능

- **좋아요 시스템**
  - 음악 및 영상에 좋아요 표시
  - 인기 콘텐츠 랭킹

- **댓글 기능**
  - 실시간 댓글 작성 및 조회
  - 사용자 간 의견 공유

### 4. 음악 월드컵

- **이상형 월드컵 스타일 게임**
  - 16강, 32강 등 다양한 라운드 지원
  - 실시간 랭킹 시스템
  - 개인별 게임 기록 저장
  - 맞춤형 월드컵 생성 및 공유

### 5. 태그 시스템

- 다양한 태그로 콘텐츠 분류
- 태그 기반 검색 및 필터링
- 관련 콘텐츠 추천

### 6. 재생 기록

- 개인별 음악/영상 재생 이력 추적
- 최근 재생 목록
- 재생 패턴 분석

## 기술 스택

### Backend

- **Framework**: Django 5.2.8
- **API**: Django REST Framework 3.16.1
- **Database**: PostgreSQL 15
- **WSGI Server**: Gunicorn 21.2.0

### Storage

- **Media Storage**: AWS S3
- **Libraries**:
  - boto3 (AWS SDK)
  - django-storages

### Media Processing

- **Video Processing**: MoviePy 2.2.1
- **Image Processing**:
  - Pillow 11.3.0
  - OpenCV 4.12.0
- **Video I/O**: ImageIO & imageio-ffmpeg

### Infrastructure

- **Containerization**: Docker & Docker Compose
- **Web Server**: Nginx 1.25
- **Database**: PostgreSQL 15 with persistent volume

### Development

- **Python**: 3.x
- **Package Manager**: pip
- **Environment**: python-dotenv

## 시스템 아키텍처

```
┌─────────────────┐
│     Client      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Nginx (Port 80)│
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Django + Gunicorn (Port 8000)  │
│  ┌──────────────────────────┐   │
│  │  Apps:                   │   │
│  │  - twobeats_account      │   │
│  │  - twobeats_upload       │   │
│  │  - twobeats_music_explore│   │
│  │  - twobeats_video_explore│   │
│  │  - twobeats_worldcup     │   │
│  └──────────────────────────┘   │
└───────┬─────────────────┬───────┘
        │                 │
        ▼                 ▼
┌──────────────┐   ┌─────────────┐
│ PostgreSQL   │   │   AWS S3    │
│ (Port 5432)  │   │  (Media)    │
└──────────────┘   └─────────────┘
```

## 설치 및 실행

### 사전 요구사항

- Python 3.9 이상
- PostgreSQL 15
- Docker & Docker Compose (선택사항)
- AWS 계정 (S3 사용 시)

### 로컬 환경 설정

1. **저장소 클론**

```bash
git clone https://github.com/thlim008/2Beats.git
cd 2Beats
```

2. **가상환경 생성 및 활성화**

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **의존성 설치**

```bash
pip install -r requirements.txt
```

4. **환경변수 설정**

`.env` 파일을 프로젝트 루트에 생성:

```env
# Database
DATABASE_URL=postgres://twobeats_user:twobeats_password@localhost:5432/twobeats_db

# Django
SECRET_KEY=your-secret-key-here
DEBUG=True

# AWS S3
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name

# PostgreSQL (Docker)
POSTGRES_DB=twobeats_db
POSTGRES_USER=twobeats_user
POSTGRES_PASSWORD=twobeats_password
```

5. **데이터베이스 마이그레이션**

```bash
python manage.py makemigrations
python manage.py migrate
```

6. **태그 데이터 초기화**

```bash
python manage.py init_tags
```

7. **관리자 계정 생성**

```bash
python manage.py createsuperuser
```

8. **정적 파일 수집**

```bash
python manage.py collectstatic
```

9. **개발 서버 실행**

```bash
python manage.py runserver
```

서버가 `http://localhost:8000`에서 실행됩니다.

### Docker Compose로 실행

```bash
docker-compose up -d
```

서비스:
- **Web**: http://localhost (Nginx를 통한 접근)
- **Database**: PostgreSQL (내부 네트워크)


리소스:
- **PersistentVolumeClaim**: 10Gi 데이터베이스 저장소
- **Database Deployment**: PostgreSQL 1 replica
- **Web Deployment**: Django 2 replicas
- **LoadBalancer Service**: 외부 접근

## 데이터베이스 구조

### 주요 테이블

#### User (사용자)
- UUID 기반 사용자 관리
- 프로필 이미지, 전화번호 확장 필드
- Django AbstractUser 상속

#### Music (음악)
- 제목, 가수, 장르, 태그
- 재생 횟수, 좋아요 수
- AWS S3 음원 파일 저장
- 자동 썸네일 생성

#### Video (영상)
- 제목, 아티스트, 타입
- 조회수, 재생 수, 좋아요 수
- 영상 시간 (초)
- AWS S3 영상 파일 저장

#### Playlist (플레이리스트)
- MusicPlaylist: 음악 전용
- VideoPlaylist: 영상 전용
- 사용자별 폴더 관리

#### WorldCup (월드컵)
- CustomWorldCup: 맞춤형 월드컵 생성
- WorldCupGame: 게임 세션 기록
- WorldCupResult: 게임 결과 및 랭킹

#### History (재생 기록)
- MusicHistory: 음악 재생 이력
- VideoHistory: 영상 재생 이력

#### Social (소셜)
- MusicLike / VideoLike: 좋아요
- MusicComment / VideoComment: 댓글

## API 문서

### 인증

Django 세션 기반 인증 사용

### 주요 엔드포인트

```
# 계정
GET    /account/login/          # 로그인 페이지
POST   /account/login/          # 로그인 처리
GET    /account/register/       # 회원가입 페이지
POST   /account/register/       # 회원가입 처리
POST   /account/logout/         # 로그아웃

# 음악
GET    /music/                  # 음악 목록
GET    /music/<id>/             # 음악 상세
POST   /music/upload/           # 음악 업로드
POST   /music/<id>/like/        # 좋아요 토글
POST   /music/<id>/comment/     # 댓글 작성

# 영상
GET    /video/                  # 영상 목록
GET    /video/<id>/             # 영상 상세
POST   /video/upload/           # 영상 업로드
POST   /video/<id>/like/        # 좋아요 토글
POST   /video/<id>/comment/     # 댓글 작성

# 플레이리스트
GET    /playlist/music/         # 음악 플레이리스트 목록
POST   /playlist/music/         # 플레이리스트 생성
POST   /playlist/music/<id>/add/# 곡 추가

# 월드컵
GET    /worldcup/               # 월드컵 목록
POST   /worldcup/custom/        # 커스텀 월드컵 생성
GET    /worldcup/play/<code>/   # 월드컵 게임
POST   /worldcup/result/        # 결과 제출
GET    /worldcup/ranking/       # 랭킹 조회
```

## 배포

### 환경 설정

프로덕션 환경에서는 다음 설정을 변경하세요:

**config/settings.py**
```python
DEBUG = False
ALLOWED_HOSTS = ['your-domain.com', 'your-ip']
SECRET_KEY = 'production-secret-key'
```

### Docker 이미지 빌드

```bash
docker build -t your-dockerhub-username/2beats:v1.3 .
docker push your-dockerhub-username/2beats:v1.3
```


## 프로젝트 구조

```
2Beats/
├── apps/                          # Django 앱들
│   ├── twobeats_account/         # 사용자 관리, 플레이리스트
│   ├── twobeats_upload/          # 미디어 업로드
│   ├── twobeats_music_explore/   # 음악 탐색 및 소셜
│   ├── twobeats_video_explore/   # 영상 탐색 및 소셜
│   └── twobeats_worldcup/        # 음악 월드컵
├── config/                        # Django 설정
│   ├── settings.py               # 프로젝트 설정
│   ├── urls.py                   # URL 라우팅
│   └── wsgi.py                   # WSGI 설정
├── static/                        # 정적 파일
├── templates/                     # HTML 템플릿
├── media/                         # 업로드된 미디어 (로컬 개발용)
├── nginx/                         # Nginx 설정
│   └── nginx.conf
├── .env                          # 환경변수 (gitignore)
├── .dockerignore
├── .gitignore
├── docker-compose.yml            # Docker Compose 설정
├── Dockerfile                    # Docker 이미지 정의
├── 2beats-k3s.yaml              # Kubernetes 배포 설정
├── requirements.txt              # Python 의존성
├── manage.py                     # Django 관리 스크립트
└── README.md                     # 프로젝트 문서
```

## 기여하기

프로젝트에 기여하고 싶으시다면:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 문의

프로젝트 관련 문의사항이 있으시면 이슈를 등록해주세요.

---

**2Beats** - 음악과 영상을 즐기는 새로운 방법
