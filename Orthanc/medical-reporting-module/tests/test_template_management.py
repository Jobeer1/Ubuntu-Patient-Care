"""
Tests for Template Management System
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import uuid
from datetime import datetime

from services.template_manager import (
    TemplateManager, TemplateConfiguration, TemplateSection, TemplateField,
    VoiceCommand, TemplateCategory, TemplateType, FieldType
)
from services.template_repository import TemplateRepository

class TestTemplateManager(unittest.TestCase):
    """Test template manager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.template_manager = TemplateManager()
    
    def test_create_template(self):
        """Test creating a new template"""
        template = self.template_manager.create_template(
            name="Test Template",
            category=TemplateCategory.GENERAL_RADIOLOGY,
            template_type=TemplateType.STRUCTURED,
            created_by="user123"
        )
        
        self.assertIsInstance(template, TemplateConfiguration)
        self.assertEqual(template.name, "Test Template")
        self.assertEqual(template.category, TemplateCategory.GENERAL_RADIOLOGY)
        self.assertEqual(template.template_type, TemplateType.STRUCTURED)
        self.assertEqual(template.created_by, "user123")
        self.assertIn(template.template_id, self.template_manager.templates)
    
    def test_get_template(self):
        """Test getting a template by ID"""
        # Create a template
        template = self.template_manager.create_template(
            "Test Template", TemplateCategory.CHEST_IMAGING
        )
        
        # Retrieve it
        retrieved = self.template_manager.get_template(template.template_id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.template_id, template.template_id)
        self.assertEqual(retrieved.name, "Test Template")
    
    def test_update_template(self):
        """Test updating a template"""
        # Create a template
        template = self.template_manager.create_template(
            "Original Name", TemplateCategory.CHEST_IMAGING
        )
        
        # Update it
        updates = {
            'name': 'Updated Name',
            'description': 'Updated description'
        }
        
        success = self.template_manager.update_template(template.template_id, updates)
        
        self.assertTrue(success)
        
        updated_template = self.template_manager.get_template(template.template_id)
        self.assertEqual(updated_template.name, 'Updated Name')
        self.assertEqual(updated_template.description, 'Updated description')
        self.assertGreater(updated_template.version, 1)
    
    def test_delete_template(self):
        """Test deleting a template"""
        # Create a template
        template = self.template_manager.create_template(
            "To Delete", TemplateCategory.CHEST_IMAGING
        )
        
        template_id = template.template_id
        
        # Delete it
        success = self.template_manager.delete_template(template_id)
        
        self.assertTrue(success)
        self.assertNotIn(template_id, self.template_manager.templates)
        
        # Try to get deleted template
        retrieved = self.template_manager.get_template(template_id)
        self.assertIsNone(retrieved)
    
    def test_search_templates(self):
        """Test template search functionality"""
        # Create test templates
        chest_template = self.template_manager.create_template(
            "Chest X-Ray Report", TemplateCategory.CHEST_IMAGING
        )
        chest_template.tags = ["chest", "xray", "radiograph"]
        
        abd_template = self.template_manager.create_template(
            "Abdominal CT", TemplateCategory.ABDOMINAL_IMAGING
        )
        abd_template.tags = ["abdomen", "ct", "contrast"]
        
        # Rebuild search index
        self.template_manager._build_search_index()
        
        # Search for chest templates
        chest_results = self.template_manager.search_templates("chest")
        self.assertGreater(len(chest_results), 0)
        
        chest_names = [t.name for t in chest_results]
        self.assertIn("Chest X-Ray Report", chest_names)
        
        # Search by category
        chest_category_results = self.template_manager.search_templates(
            "", category=TemplateCategory.CHEST_IMAGING
        )
        self.assertGreater(len(chest_category_results), 0)
        
        # Search for non-existent term
        no_results = self.template_manager.search_templates("nonexistent")
        # Should return empty list or very few results
        self.assertLessEqual(len(no_results), 1)
    
    def test_get_templates_by_category(self):
        """Test getting templates by category"""
        # Create templates in different categories
        chest_template = self.template_manager.create_template(
            "Chest Template", TemplateCategory.CHEST_IMAGING
        )
        
        neuro_template = self.template_manager.create_template(
            "Brain MRI", TemplateCategory.NEUROIMAGING
        )
        
        # Get chest imaging templates
        chest_templates = self.template_manager.get_templates_by_category(
            TemplateCategory.CHEST_IMAGING
        )
        
        self.assertGreater(len(chest_templates), 0)
        
        # Check that all returned templates are chest imaging
        for template in chest_templates:
            self.assertEqual(template.category, TemplateCategory.CHEST_IMAGING)
    
    def test_clone_template(self):
        """Test cloning a template"""
        # Create original template
        original = self.template_manager.create_template(
            "Original Template", TemplateCategory.CHEST_IMAGING
        )
        original.description = "Original description"
        original.tags = ["original", "test"]
        
        # Clone it
        cloned = self.template_manager.clone_template(
            original.template_id, "Cloned Template", "user456"
        )
        
        self.assertIsNotNone(cloned)
        self.assertNotEqual(cloned.template_id, original.template_id)
        self.assertEqual(cloned.name, "Cloned Template")
        self.assertEqual(cloned.category, original.category)
        self.assertEqual(cloned.created_by, "user456")
        self.assertEqual(cloned.tags, original.tags)
        self.assertEqual(cloned.version, 1)
        self.assertEqual(cloned.usage_count, 0)
    
    def test_add_section(self):
        """Test adding a section to a template"""
        # Create a template
        template = self.template_manager.create_template(
            "Test Template", TemplateCategory.GENERAL_RADIOLOGY
        )
        
        # Create a section
        section = TemplateSection(
            section_id="test_section",
            section_name="test_section",
            title="Test Section",
            description="A test section"
        )
        
        # Add section to template
        success = self.template_manager.add_section(template.template_id, section)
        
        self.assertTrue(success)
        
        # Verify section was added
        updated_template = self.template_manager.get_template(template.template_id)
        section_ids = [s.section_id for s in updated_template.sections]
        self.assertIn("test_section", section_ids)
    
    def test_add_field(self):
        """Test adding a field to a template section"""
        # Create a template with a section
        template = self.template_manager.create_template(
            "Test Template", TemplateCategory.GENERAL_RADIOLOGY
        )
        
        section = TemplateSection(
            section_id="test_section",
            section_name="test_section",
            title="Test Section"
        )
        
        self.template_manager.add_section(template.template_id, section)
        
        # Create a field
        field = TemplateField(
            field_id="test_field",
            field_name="test_field",
            field_type=FieldType.TEXT,
            label="Test Field",
            description="A test field"
        )
        
        # Add field to section
        success = self.template_manager.add_field(
            template.template_id, "test_section", field
        )
        
        self.assertTrue(success)
        
        # Verify field was added
        updated_template = self.template_manager.get_template(template.template_id)
        test_section = None
        for s in updated_template.sections:
            if s.section_id == "test_section":
                test_section = s
                break
        
        self.assertIsNotNone(test_section)
        field_ids = [f.field_id for f in test_section.fields]
        self.assertIn("test_field", field_ids)
    
    def test_voice_command_registration(self):
        """Test voice command registration"""
        # Create a template
        template = self.template_manager.create_template(
            "Voice Template", TemplateCategory.CHEST_IMAGING
        )
        
        # Create a voice command
        voice_cmd = VoiceCommand(
            command_id="test_voice_cmd",
            command_text="load voice template",
            command_variations=["voice template", "template voice"],
            action_type="load_template",
            target_id=template.template_id
        )
        
        # Register voice command
        success = self.template_manager.register_voice_command(voice_cmd)
        
        self.assertTrue(success)
        self.assertIn("test_voice_cmd", self.template_manager.voice_commands)
        
        # Get voice commands for template
        template_commands = self.template_manager.get_voice_commands(template.template_id)
        self.assertGreater(len(template_commands), 0)
        
        command_texts = [cmd.command_text for cmd in template_commands]
        self.assertIn("load voice template", command_texts)
    
    def test_voice_command_processing(self):
        """Test voice command processing"""
        # Use existing default template
        chest_template_id = "chest_xray_template"
        
        # Process voice command
        result = self.template_manager.process_voice_command("chest x-ray template", 0.9)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['action'], 'load_template')
        self.assertEqual(result['template_id'], chest_template_id)
        
        # Test command variation
        result2 = self.template_manager.process_voice_command("chest xray", 0.9)
        self.assertIsNotNone(result2)
        
        # Test non-existent command
        result3 = self.template_manager.process_voice_command("nonexistent command", 0.9)
        self.assertIsNone(result3)
    
    def test_template_statistics(self):
        """Test template statistics"""
        # Create some test templates
        for i in range(3):
            template = self.template_manager.create_template(
                f"Test Template {i}", TemplateCategory.CHEST_IMAGING
            )
            template.usage_count = i * 5  # Different usage counts
        
        stats = self.template_manager.get_template_statistics()
        
        self.assertIn('total_templates', stats)
        self.assertIn('active_templates', stats)
        self.assertIn('categories', stats)
        self.assertIn('most_used', stats)
        self.assertIn('recent_templates', stats)
        
        self.assertGreater(stats['total_templates'], 0)
        self.assertIsInstance(stats['most_used'], list)
        self.assertIsInstance(stats['recent_templates'], list)
    
    def test_export_import_template(self):
        """Test template export and import"""
        # Create a template
        original = self.template_manager.create_template(
            "Export Test", TemplateCategory.CHEST_IMAGING
        )
        original.description = "Test description"
        original.tags = ["export", "test"]
        
        # Export template
        exported_data = self.template_manager.export_template(original.template_id)
        
        self.assertIsNotNone(exported_data)
        self.assertEqual(exported_data['name'], "Export Test")
        self.assertEqual(exported_data['description'], "Test description")
        
        # Import template
        imported = self.template_manager.import_template(exported_data, "user789")
        
        self.assertIsNotNone(imported)
        self.assertNotEqual(imported.template_id, original.template_id)  # Should have new ID
        self.assertEqual(imported.name, "Export Test")
        self.assertEqual(imported.description, "Test description")
        self.assertEqual(imported.created_by, "user789")
        self.assertEqual(imported.version, 1)
        self.assertEqual(imported.usage_count, 0)

class TestTemplateRepository(unittest.TestCase):
    """Test template repository functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.repository = TemplateRepository()
        
        # Mock database session
        self.mock_session = Mock()
        self.mock_db_session = patch('services.template_repository.get_db_session')
        self.mock_db_session.start().return_value.__enter__.return_value = self.mock_session
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.mock_db_session.stop()
    
    def test_save_template(self):
        """Test saving a template to database"""
        # Create test template
        template = TemplateConfiguration(
            template_id="test_template_123",
            name="Test Template",
            category=TemplateCategory.CHEST_IMAGING,
            template_type=TemplateType.STRUCTURED,
            created_by="user123"
        )
        
        # Mock database operations
        self.mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Save template
        success = self.repository.save_template(template)
        
        self.assertTrue(success)
        self.mock_session.add.assert_called_once()
        self.mock_session.commit.assert_called_once()
    
    def test_load_template(self):
        """Test loading a template from database"""
        # Mock database record
        mock_record = Mock()
        mock_record.template_id = "test_template_123"
        mock_record.name = "Test Template"
        mock_record.category = "chest_imaging"
        mock_record.template_type = "structured"
        mock_record.description = "Test description"
        mock_record.specialty = "Radiology"
        mock_record.procedure_type = "Chest X-Ray"
        mock_record.template_data = {
            'template_id': 'test_template_123',
            'name': 'Test Template',
            'sections': [],
            'voice_commands': []
        }
        mock_record.tags = '["test", "template"]'
        mock_record.is_active = True
        mock_record.is_shared = False
        mock_record.created_by = "user123"
        mock_record.created_at = datetime.utcnow()
        mock_record.modified_at = datetime.utcnow()
        mock_record.version = 1
        mock_record.usage_count = 0
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = mock_record
        
        # Load template
        template = self.repository.load_template("test_template_123")
        
        self.assertIsNotNone(template)
        self.assertEqual(template.template_id, "test_template_123")
        self.assertEqual(template.name, "Test Template")
        self.assertEqual(template.category, TemplateCategory.CHEST_IMAGING)
    
    def test_search_templates(self):
        """Test searching templates in database"""
        # Mock database records
        mock_records = []
        for i in range(3):
            mock_record = Mock()
            mock_record.template_id = f"template_{i}"
            mock_record.name = f"Template {i}"
            mock_record.category = "chest_imaging"
            mock_record.template_type = "structured"
            mock_record.description = f"Description {i}"
            mock_record.specialty = "Radiology"
            mock_record.procedure_type = "Test"
            mock_record.template_data = {
                'template_id': f'template_{i}',
                'name': f'Template {i}',
                'sections': [],
                'voice_commands': []
            }
            mock_record.tags = '[]'
            mock_record.is_active = True
            mock_record.is_shared = False
            mock_record.created_by = "user123"
            mock_record.created_at = datetime.utcnow()
            mock_record.modified_at = datetime.utcnow()
            mock_record.version = 1
            mock_record.usage_count = i
            mock_records.append(mock_record)
        
        self.mock_session.query.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_records
        
        # Search templates
        results = self.repository.search_templates("template", limit=10)
        
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].name, "Template 0")
    
    def test_cache_functionality(self):
        """Test template caching"""
        # Create test template
        template = TemplateConfiguration(
            template_id="cached_template_123",
            name="Cached Template",
            category=TemplateCategory.CHEST_IMAGING,
            template_type=TemplateType.STRUCTURED
        )
        
        # Add to cache
        self.repository.cache[template.template_id] = template
        self.repository.cache_expiry[template.template_id] = datetime.utcnow()
        
        # Load from cache (should not hit database)
        loaded_template = self.repository.load_template("cached_template_123")
        
        self.assertIsNotNone(loaded_template)
        self.assertEqual(loaded_template.template_id, "cached_template_123")
        self.mock_session.query.assert_not_called()
    
    def test_update_usage_count(self):
        """Test updating template usage count"""
        # Mock database record
        mock_record = Mock()
        mock_record.usage_count = 5
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = mock_record
        
        # Update usage count
        success = self.repository.update_usage_count("test_template")
        
        self.assertTrue(success)
        self.assertEqual(mock_record.usage_count, 6)
        self.mock_session.commit.assert_called_once()

class TestTemplateIntegration(unittest.TestCase):
    """Integration tests for template management system"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.template_manager = TemplateManager()
        self.repository = TemplateRepository()
    
    def test_complete_template_workflow(self):
        """Test complete template management workflow"""
        # 1. Create a new template
        template = self.template_manager.create_template(
            "Integration Test Template",
            TemplateCategory.CHEST_IMAGING,
            TemplateType.STRUCTURED,
            "user123"
        )
        
        self.assertIsNotNone(template)
        
        # 2. Add sections and fields
        section = TemplateSection(
            section_id="findings",
            section_name="findings",
            title="Findings",
            description="Clinical findings section"
        )
        
        success = self.template_manager.add_section(template.template_id, section)
        self.assertTrue(success)
        
        field = TemplateField(
            field_id="lungs",
            field_name="lungs",
            field_type=FieldType.TEXTAREA,
            label="Lungs",
            description="Lung findings",
            default_value="The lungs are clear.",
            voice_commands=["lungs", "lung fields"]
        )
        
        success = self.template_manager.add_field(template.template_id, "findings", field)
        self.assertTrue(success)
        
        # 3. Register voice commands
        voice_cmd = VoiceCommand(
            command_id="load_integration_template",
            command_text="integration test template",
            command_variations=["integration template"],
            action_type="load_template",
            target_id=template.template_id
        )
        
        success = self.template_manager.register_voice_command(voice_cmd)
        self.assertTrue(success)
        
        # 4. Test voice command processing
        result = self.template_manager.process_voice_command("integration test template", 0.9)
        self.assertIsNotNone(result)
        self.assertEqual(result['action'], 'load_template')
        self.assertEqual(result['template_id'], template.template_id)
        
        # 5. Test search functionality
        search_results = self.template_manager.search_templates("integration")
        self.assertGreater(len(search_results), 0)
        
        template_names = [t.name for t in search_results]
        self.assertIn("Integration Test Template", template_names)
        
        # 6. Clone the template
        cloned = self.template_manager.clone_template(
            template.template_id, "Cloned Integration Template", "user456"
        )
        
        self.assertIsNotNone(cloned)
        self.assertEqual(len(cloned.sections), len(template.sections))
        
        # 7. Export and import
        exported_data = self.template_manager.export_template(template.template_id)
        self.assertIsNotNone(exported_data)
        
        imported = self.template_manager.import_template(exported_data, "user789")
        self.assertIsNotNone(imported)
        self.assertEqual(imported.name, template.name)
    
    def test_default_templates_functionality(self):
        """Test that default templates work correctly"""
        # Test chest x-ray template
        chest_template = self.template_manager.get_template("chest_xray_template")
        self.assertIsNotNone(chest_template)
        self.assertEqual(chest_template.name, "Chest X-Ray")
        self.assertEqual(chest_template.category, TemplateCategory.CHEST_IMAGING)
        
        # Test that it has sections
        self.assertGreater(len(chest_template.sections), 0)
        
        # Test that sections have fields
        for section in chest_template.sections:
            if section.section_id == "findings":
                self.assertGreater(len(section.fields), 0)
                break
        
        # Test voice commands
        voice_commands = self.template_manager.get_voice_commands("chest_xray_template")
        self.assertGreater(len(voice_commands), 0)
        
        # Test voice command processing
        result = self.template_manager.process_voice_command("chest x-ray template", 0.9)
        self.assertIsNotNone(result)
        self.assertEqual(result['template_id'], "chest_xray_template")

if __name__ == '__main__':
    unittest.main()