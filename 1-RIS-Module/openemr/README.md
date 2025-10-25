# SA OpenEMR RIS & Medical Billing System

A comprehensive, production-ready Radiology Information System (RIS) and medical billing platform specifically designed for the South African healthcare market. Built with modern technologies and integrated with South African medical aid schemes and the Healthbridge clearing house.

## 🏥 Features

### Core Functionality
- **Patient Management**: Complete patient registration, demographics, and medical history
- **Study Order Management**: Radiology procedure ordering and workflow tracking
- **Claims Processing**: Automated claim generation and submission to medical aid schemes
- **Medical Aid Integration**: Real-time verification with Discovery Health, Momentum, Bonitas, GEMS, and more
- **Healthbridge Integration**: Direct integration with South Africa's leading clearing house
- **PACS Integration**: Seamless connection with Orthanc PACS system
- **Real-time Workflow**: Live status updates and notifications

### South African Specific Features
- **ICD-10 Code Management**: Complete South African ICD-10 code database with validation
- **NRPL Billing Codes**: National Reference Price List integration with current tariffs
- **Medical Aid Schemes**: Support for all major SA medical aid schemes
- **POPIA Compliance**: Full compliance with Protection of Personal Information Act
- **VAT Handling**: Proper South African VAT calculations and exemptions

### Technical Features
- **Offline-First**: Continue working during internet outages with automatic sync
- **Real-time Updates**: Socket.io integration for live system updates
- **Role-Based Access**: Comprehensive user management with role-based permissions
- **Audit Logging**: Complete audit trail for compliance and security
- **Professional UI**: Modern, responsive interface built with Material-UI
- **API-First**: RESTful API design with comprehensive documentation

## 🚀 Technology Stack

### Backend
- **Node.js** with **Express.js** - Robust server framework
- **TypeScript** - Type-safe development
- **PostgreSQL** - Primary database with ACID compliance
- **Prisma ORM** - Modern database toolkit
- **Redis** - Caching and session management
- **Socket.io** - Real-time communication
- **JWT** - Secure authentication
- **Winston** - Comprehensive logging

### Frontend
- **React 18** with **TypeScript** - Modern UI framework
- **Material-UI (MUI)** - Professional component library
- **React Query** - Efficient data fetching and caching
- **React Router** - Client-side routing
- **Socket.io Client** - Real-time updates
- **React Hook Form** - Form management
- **Chart.js** - Data visualization

### Infrastructure
- **Docker** - Containerized deployment
- **Nginx** - Reverse proxy and load balancing
- **SSL/TLS** - End-to-end encryption
- **Automated Backups** - Point-in-time recovery

## 📋 Prerequisites

- Node.js 18+ and npm
- PostgreSQL 15+
- Redis 7+
- Docker and Docker Compose (optional)

## 🛠️ Installation

### Option 1: Docker Setup (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd openemr
   ```

2. **Start with Docker Compose**
   ```bash
   docker-compose up -d
   ```

3. **Run database migrations**
   ```bash
   npm run db:migrate
   npm run db:seed
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:3001
   - Database: localhost:5432

### Option 2: Manual Setup

1. **Install dependencies**
   ```bash
   # Install root dependencies
   npm install
   
   # Install server dependencies
   cd server && npm install
   
   # Install client dependencies
   cd ../client && npm install
   ```

2. **Set up environment variables**
   ```bash
   # Copy environment files
   cp server/.env.example server/.env
   cp client/.env.example client/.env
   
   # Edit the .env files with your configuration
   ```

3. **Set up the database**
   ```bash
   # Start PostgreSQL and Redis
   # Then run migrations
   cd server
   npx prisma migrate dev
   npx prisma db seed
   ```

4. **Start the development servers**
   ```bash
   # From the root directory
   npm run dev
   ```

## 🔐 Default Login Credentials

```
Email: admin@openemr.co.za
Password: admin123
```

## 📊 Database Schema

The system uses a comprehensive PostgreSQL schema with the following main entities:

- **Users**: System users with role-based access
- **Patients**: Patient demographics and medical information
- **Medical Aid Schemes**: Configuration for SA medical aid schemes
- **Study Orders**: Radiology procedure orders and workflow
- **Claims**: Medical aid claims and billing information
- **NRPL Codes**: National Reference Price List codes
- **ICD-10 Codes**: International Classification of Diseases codes
- **Audit Logs**: Complete system audit trail

## 🔌 API Documentation

The API follows RESTful principles with comprehensive endpoints:

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `GET /api/auth/verify` - Token verification

### Patients
- `GET /api/patients` - List patients with search and pagination
- `POST /api/patients` - Create new patient
- `GET /api/patients/:id` - Get patient details
- `PUT /api/patients/:id` - Update patient
- `POST /api/patients/:id/verify-medical-aid` - Verify medical aid

### Study Orders
- `GET /api/study-orders` - List study orders
- `POST /api/study-orders` - Create study order
- `PATCH /api/study-orders/:id/status` - Update order status

### Claims
- `GET /api/claims` - List claims
- `POST /api/claims` - Create claim
- `GET /api/claims/:id` - Get claim details

## 🏥 Medical Aid Integration

The system integrates with major South African medical aid schemes:

- **Discovery Health Medical Scheme** - Real-time member verification and pre-authorization
- **Momentum Health** - Benefit checking and claim submission
- **Bonitas Medical Fund** - Electronic claims processing
- **GEMS** - Government employee scheme support
- **Bestmed** - Automated billing and claims

### Healthbridge Integration

Direct integration with Healthbridge clearing house for:
- Electronic claim submission
- Real-time claim status tracking
- Payment reconciliation
- Automated remittance processing

## 🔒 Security & Compliance

### POPIA Compliance
- Data encryption at rest and in transit
- Comprehensive audit logging
- User consent management
- Secure data deletion
- Access control and monitoring

### Security Features
- JWT-based authentication
- Role-based access control
- Rate limiting and DDoS protection
- Input validation and sanitization
- SQL injection prevention
- XSS protection

## 📈 Monitoring & Logging

- **Winston Logging**: Comprehensive application logging
- **Audit Trails**: Complete user activity tracking
- **System Monitoring**: Real-time system health checks
- **Performance Metrics**: API response times and usage statistics
- **Error Tracking**: Automated error detection and alerting

## 🧪 Testing

```bash
# Run server tests
cd server && npm test

# Run client tests
cd client && npm test

# Run end-to-end tests
npm run test:e2e
```

## 📦 Deployment

### Production Deployment

1. **Build the application**
   ```bash
   npm run build
   ```

2. **Set up production environment**
   ```bash
   # Configure production environment variables
   # Set up SSL certificates
   # Configure database backups
   ```

3. **Deploy with Docker**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Contact the Ubuntu Patient Sorg team
- Check the documentation wiki

## 🎯 Roadmap

### Phase 1 (Current)
- ✅ Core patient management
- ✅ Basic medical aid integration
- ✅ User authentication and authorization
- ✅ Database schema and API foundation

### Phase 2 (Next)
- 🔄 Complete study order workflow
- 🔄 Full claims processing
- 🔄 PACS integration
- 🔄 Advanced reporting

### Phase 3 (Future)
- 📋 Mobile application
- 📋 Advanced analytics
- 📋 AI-powered insights
- 📋 Multi-practice support

---

**Built with ❤️ by the Ubuntu Patient Sorg Team**

*Revolutionizing South African healthcare technology*