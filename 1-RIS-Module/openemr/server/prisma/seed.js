"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const client_1 = require("@prisma/client");
const bcryptjs_1 = __importDefault(require("bcryptjs"));
const prisma = new client_1.PrismaClient();
async function main() {
    console.log('🌱 Starting database seeding...');
    // Create admin user
    const hashedPassword = await bcryptjs_1.default.hash('admin123', 10);
    const adminUser = await prisma.user.upsert({
        where: { email: 'admin@openemr.co.za' },
        update: {},
        create: {
            email: 'admin@openemr.co.za',
            password: hashedPassword,
            firstName: 'System',
            lastName: 'Administrator',
            role: 'ADMIN',
        },
    });
    console.log('✅ Admin user created:', adminUser.email);
    // Seed Medical Aid Schemes
    const medicalAidSchemes = [
        {
            code: 'DHMS',
            name: 'Discovery Health Medical Scheme',
            apiEndpoint: 'https://api.discovery.co.za/health/v1',
            authenticationMethod: 'OAUTH2',
            preAuthRequired: JSON.stringify(['3014', '3021', '3024']), // CT and MRI procedures
            contactPhone: '0860 99 88 77',
            contactEmail: 'providers@discovery.co.za',
        },
        {
            code: 'MOM',
            name: 'Momentum Health',
            apiEndpoint: 'https://api.momentum.co.za/health/v2',
            authenticationMethod: 'API_KEY',
            preAuthRequired: JSON.stringify(['3014', '3021', '3024', '3031']),
            contactPhone: '0860 11 11 11',
            contactEmail: 'providers@momentum.co.za',
        },
        {
            code: 'BON',
            name: 'Bonitas Medical Fund',
            apiEndpoint: 'https://api.bonitas.co.za/v1',
            authenticationMethod: 'BASIC',
            preAuthRequired: JSON.stringify(['3021', '3024']),
            contactPhone: '0860 002 108',
            contactEmail: 'providers@bonitas.co.za',
        },
        {
            code: 'GEMS',
            name: 'Government Employees Medical Scheme',
            apiEndpoint: 'https://api.gems.gov.za/v1',
            authenticationMethod: 'API_KEY',
            preAuthRequired: JSON.stringify(['3014', '3021', '3024']),
            contactPhone: '0860 436 769',
            contactEmail: 'providers@gems.gov.za',
        },
        {
            code: 'BESTMED',
            name: 'Bestmed Medical Scheme',
            apiEndpoint: 'https://api.bestmed.co.za/v1',
            authenticationMethod: 'OAUTH2',
            preAuthRequired: JSON.stringify(['3021', '3024']),
            contactPhone: '0860 002 378',
            contactEmail: 'providers@bestmed.co.za',
        },
    ];
    for (const scheme of medicalAidSchemes) {
        await prisma.medicalAidScheme.upsert({
            where: { code: scheme.code },
            update: {},
            create: scheme,
        });
    }
    console.log('✅ Medical Aid Schemes seeded');
    // Seed NRPL Codes
    const nrplCodes = [
        {
            code: '3001',
            description: 'Chest X-Ray PA',
            category: 'X-Ray',
            baseRate: 320.00,
            vatApplicable: false,
            effectiveDate: new Date('2024-01-01'),
            relatedICD10: JSON.stringify(['R06.02', 'R50.9', 'Z87.891']),
        },
        {
            code: '3002',
            description: 'Chest X-Ray Lateral',
            category: 'X-Ray',
            baseRate: 280.00,
            vatApplicable: false,
            effectiveDate: new Date('2024-01-01'),
            relatedICD10: JSON.stringify(['R06.02', 'R50.9']),
        },
        {
            code: '3011',
            description: 'CT Head without contrast',
            category: 'CT',
            baseRate: 1850.00,
            vatApplicable: false,
            effectiveDate: new Date('2024-01-01'),
            relatedICD10: JSON.stringify(['R51', 'G93.1', 'S06.9']),
        },
        {
            code: '3014',
            description: 'CT Chest with contrast',
            category: 'CT',
            baseRate: 2850.00,
            vatApplicable: false,
            effectiveDate: new Date('2024-01-01'),
            relatedICD10: JSON.stringify(['R06.02', 'R50.9', 'C78.00']),
        },
        {
            code: '3021',
            description: 'MRI Brain without contrast',
            category: 'MRI',
            baseRate: 4500.00,
            vatApplicable: false,
            effectiveDate: new Date('2024-01-01'),
            relatedICD10: JSON.stringify(['R51', 'G93.1', 'G93.9']),
        },
        {
            code: '3024',
            description: 'MRI Lumbar Spine',
            category: 'MRI',
            baseRate: 4200.00,
            vatApplicable: false,
            effectiveDate: new Date('2024-01-01'),
            relatedICD10: JSON.stringify(['M54.5', 'M51.9', 'M48.06']),
        },
        {
            code: '3031',
            description: 'Ultrasound Abdomen',
            category: 'Ultrasound',
            baseRate: 850.00,
            vatApplicable: false,
            effectiveDate: new Date('2024-01-01'),
            relatedICD10: JSON.stringify(['R10.9', 'K59.1', 'R14.0']),
        },
        {
            code: '3041',
            description: 'Mammography Bilateral',
            category: 'Mammography',
            baseRate: 1200.00,
            vatApplicable: false,
            effectiveDate: new Date('2024-01-01'),
            relatedICD10: JSON.stringify(['Z12.31', 'N60.1', 'C50.9']),
        },
    ];
    for (const code of nrplCodes) {
        await prisma.nRPLCode.upsert({
            where: { code: code.code },
            update: {},
            create: code,
        });
    }
    console.log('✅ NRPL Codes seeded');
    // Seed ICD-10 Codes
    const icd10Codes = [
        { code: 'R06.02', description: 'Shortness of breath', category: 'Respiratory' },
        { code: 'R50.9', description: 'Fever, unspecified', category: 'General' },
        { code: 'R51', description: 'Headache', category: 'Neurological' },
        { code: 'R10.9', description: 'Unspecified abdominal pain', category: 'Digestive' },
        { code: 'M54.5', description: 'Low back pain', category: 'Musculoskeletal' },
        { code: 'M25.50', description: 'Pain in unspecified joint', category: 'Musculoskeletal' },
        { code: 'R06.00', description: 'Dyspnea, unspecified', category: 'Respiratory' },
        { code: 'G93.1', description: 'Anoxic brain damage, not elsewhere classified', category: 'Neurological' },
        { code: 'S06.9', description: 'Unspecified intracranial injury', category: 'Injury' },
        { code: 'C78.00', description: 'Secondary malignant neoplasm of unspecified lung', category: 'Neoplasm' },
        { code: 'M51.9', description: 'Unspecified thoracic, thoracolumbar and lumbosacral intervertebral disc disorder', category: 'Musculoskeletal' },
        { code: 'Z12.31', description: 'Encounter for screening mammogram for malignant neoplasm of breast', category: 'Screening' },
        { code: 'N60.1', description: 'Diffuse cystic mastopathy', category: 'Reproductive' },
        { code: 'C50.9', description: 'Malignant neoplasm of unspecified site of unspecified female breast', category: 'Neoplasm' },
        { code: 'Z87.891', description: 'Personal history of nicotine dependence', category: 'History' },
    ];
    for (const code of icd10Codes) {
        await prisma.iCD10Code.upsert({
            where: { code: code.code },
            update: {},
            create: code,
        });
    }
    console.log('✅ ICD-10 Codes seeded');
    // Seed System Configuration
    const systemConfigs = [
        { key: 'HEALTHBRIDGE_API_URL', value: 'https://api.healthbridge.co.za/v2' },
        { key: 'PRACTICE_NAME', value: 'Ubuntu Patient Sorg Radiology' },
        { key: 'PRACTICE_CODE', value: 'UPS001' },
        { key: 'VAT_RATE', value: '0.15' },
        { key: 'AUTO_SUBMIT_CLAIMS', value: 'true' },
        { key: 'EMAIL_NOTIFICATIONS', value: 'true' },
        { key: 'SYNC_INTERVAL_MINUTES', value: '5' },
    ];
    for (const config of systemConfigs) {
        await prisma.systemConfig.upsert({
            where: { key: config.key },
            update: {},
            create: config,
        });
    }
    console.log('✅ System Configuration seeded');
    console.log('🎉 Database seeding completed successfully!');
}
main()
    .catch((e) => {
    console.error('❌ Error during seeding:', e);
    process.exit(1);
})
    .finally(async () => {
    await prisma.$disconnect();
});
//# sourceMappingURL=seed.js.map