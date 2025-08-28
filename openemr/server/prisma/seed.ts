import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcryptjs';

const prisma = new PrismaClient();

async function main() {
  console.log('🌱 Starting database seeding...');

  // Create demo user
  const hashedPassword = await bcrypt.hash('demo123', 12);
  const demoUser = await prisma.user.upsert({
    where: { email: 'demo@example.com' },
    update: {
      password: hashedPassword, // Update password if user exists
    },
    create: {
      email: 'demo@example.com',
      password: hashedPassword,
      firstName: 'Demo',
      lastName: 'User',
    },
  });

  console.log('✅ Demo user created:', demoUser.email);

  // Create some sample tasks for the demo user
  const sampleTasks = [
    {
      title: 'Welcome to OpenEMR RIS!',
      description: 'This is your first task. You can edit or delete it.',
      priority: 'HIGH',
      userId: demoUser.id,
    },
    {
      title: 'Review patient records',
      description: 'Check the patient management system and add new patients.',
      priority: 'MEDIUM',
      userId: demoUser.id,
    },
    {
      title: 'Process pending claims',
      description: 'Review and submit pending medical aid claims.',
      priority: 'HIGH',
      userId: demoUser.id,
    },
    {
      title: 'Generate monthly reports',
      description: 'Create financial and operational reports for the month.',
      priority: 'LOW',
      userId: demoUser.id,
    },
  ];

  for (const taskData of sampleTasks) {
    await prisma.task.create({
      data: taskData,
    });
  }

  console.log('✅ Sample tasks created');

  // Create some sample notes
  const sampleNotes = [
    {
      title: 'Welcome to OpenEMR RIS',
      content: 'Welcome to your Radiology Information System! This system includes:\n\n• Patient Management\n• Study Orders\n• Billing & Claims\n• Reports & Analytics\n• Task Management\n• Notes System\n\nFeel free to explore all the features.',
      userId: demoUser.id,
    },
    {
      title: 'System Features',
      content: 'Key features of this RIS:\n\n1. **Patient Management** - Complete patient records\n2. **Study Orders** - Radiology ordering system\n3. **Billing** - Invoice and payment tracking\n4. **Claims** - Medical aid claims processing\n5. **Reports** - Analytics and business intelligence\n6. **Tasks** - Personal task management\n7. **Notes** - Note-taking system',
      userId: demoUser.id,
    },
    {
      title: 'Demo Credentials',
      content: 'Demo login credentials:\n\nEmail: demo@example.com\nPassword: demo123\n\nThis account has full access to all system features for testing purposes.',
      userId: demoUser.id,
    },
  ];

  for (const noteData of sampleNotes) {
    await prisma.note.create({
      data: noteData,
    });
  }

  console.log('✅ Sample notes created');

  console.log('🎉 Database seeding completed successfully!');
  console.log('');
  console.log('📋 Demo Login Credentials:');
  console.log('   Email: demo@example.com');
  console.log('   Password: demo123');
  console.log('');
  console.log('🌐 Access the system at: http://localhost:3000');
}

main()
  .catch((e) => {
    console.error('❌ Error during seeding:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });