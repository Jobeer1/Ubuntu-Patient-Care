const { PrismaClient } = require('@prisma/client');
const bcrypt = require('bcryptjs');

const prisma = new PrismaClient();

async function createDemoUser() {
  try {
    console.log('🔧 Creating demo user...');
    
    // Hash password
    const hashedPassword = await bcrypt.hash('demo123', 12);
    
    // Create or update demo user
    const demoUser = await prisma.user.upsert({
      where: { email: 'demo@example.com' },
      update: {
        password: hashedPassword,
        firstName: 'Demo',
        lastName: 'User',
        isActive: true,
      },
      create: {
        email: 'demo@example.com',
        password: hashedPassword,
        firstName: 'Demo',
        lastName: 'User',
        isActive: true,
      },
    });

    console.log('✅ Demo user created/updated successfully!');
    console.log('📧 Email: demo@example.com');
    console.log('🔑 Password: demo123');
    
    // Also create admin user for testing
    const adminPassword = await bcrypt.hash('admin123', 12);
    const adminUser = await prisma.user.upsert({
      where: { email: 'admin@openemr.co.za' },
      update: {
        password: adminPassword,
        firstName: 'Admin',
        lastName: 'User',
        isActive: true,
      },
      create: {
        email: 'admin@openemr.co.za',
        password: adminPassword,
        firstName: 'Admin',
        lastName: 'User',
        isActive: true,
      },
    });

    console.log('✅ Admin user created/updated successfully!');
    console.log('📧 Email: admin@openemr.co.za');
    console.log('🔑 Password: admin123');
    
  } catch (error) {
    console.error('❌ Error creating demo user:', error);
  } finally {
    await prisma.$disconnect();
  }
}

createDemoUser();