# BlackEagles Odoo Module Development Guidelines

This document provides guidelines and instructions for developing and maintaining the BlackEagles Odoo modules, specifically the `an_ClubMgnt` module for club management.

## Table of Contents

1. [Build and Configuration Instructions](#build-and-configuration-instructions)
2. [Testing Information](#testing-information)
3. [Development Guidelines](#development-guidelines)
4. [Module Structure](#module-structure)
5. [Resources](#resources)

---

## Build and Configuration Instructions

### Prerequisites

- Odoo 17.0 Community Edition
- Python 3.10+
- PostgreSQL 12+
- Node.js and npm (for frontend development)

### Installation

1. **Clone the Odoo repository**:
   ```bash
   git clone https://github.com/odoo/odoo.git --depth 1 --branch 17.0 /path/to/odoo
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r /path/to/odoo/requirements.txt
   ```

3. **Install the module**:
   - Copy the `an_ClubMgnt` directory to your Odoo addons path
   - Alternatively, add the module's parent directory to your addons path in the Odoo configuration

4. **Configure Odoo**:
   Create or edit your Odoo configuration file (typically `odoo.conf`):
   ```ini
   [options]
   addons_path = /path/to/odoo/addons,/path/to/custom/addons
   db_host = localhost
   db_port = 5432
   db_user = odoo
   db_password = your_password
   db_name = your_database
   ```

5. **Initialize the database**:
   ```bash
   python /path/to/odoo/odoo-bin -c /path/to/odoo.conf -d your_database -i base
   ```

6. **Install the module**:
   - Via command line:
     ```bash
     python /path/to/odoo/odoo-bin -c /path/to/odoo.conf -d your_database -i an_ClubMgnt
     ```
   - Or via the Odoo web interface:
     - Go to Apps
     - Remove the "Apps" filter
     - Search for "Club Management"
     - Click Install

### Module Dependencies

The `an_ClubMgnt` module depends on:
- `website_event_sale`
- `website_sale`
- `theme_prime`

Ensure these modules are installed before installing `an_ClubMgnt`.

---

## Testing Information

### Test Configuration

1. **Create a test database**:
   ```bash
   python /path/to/odoo/odoo-bin -c /path/to/odoo.conf -d test_database --stop-after-init
   ```

2. **Run tests for the module**:
   ```bash
   python /path/to/odoo/odoo-bin -c /path/to/odoo.conf -d test_database --test-enable --log-level=test -i an_ClubMgnt
   ```

### Writing Tests

Tests in Odoo follow the standard Python unittest framework with some Odoo-specific additions. Tests should be placed in a `tests` directory within the module.

#### Test Structure

1. Create a `tests` directory in your module
2. Add an `__init__.py` file to import your test files
3. Create test files with names starting with `test_`

#### Example Test

Here's a simple test for the `club.member` model:

```python
# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

class TestClubMember(TransactionCase):
    def setUp(self):
        super(TestClubMember, self).setUp()
        # Create test data
        self.club = self.env['club.club'].create({
            'name': 'Test Club',
            'street': 'Test Street',
            'city': 'Test City',
            'zipcode': '12345',
        })
        
        # Create a test member
        self.member = self.env['club.member'].create({
            'member_name': 'Test',
            'member_surname': 'Member',
            'email': 'test.member@example.com',
            'mobile': '1234567890',
            'club_id': self.club.id,
            'member_type': 'member',
        })

    def test_compute_name(self):
        """Test that the name is correctly computed from member_surname and member_name"""
        self.assertEqual(self.member.name, 'Member Test', 
                         "Name should be computed as 'Member Test'")
        
    def test_compute_age(self):
        """Test that age is correctly computed from birthday"""
        # Set a birthday
        self.member.write({'birthday': '1990-01-01'})
        
        # Check that age is computed (exact value will depend on current date)
        self.assertTrue(self.member.age_member > 0, 
                        "Age should be computed from birthday")
```

### Test Types

- **TransactionCase**: For testing model methods and business logic
- **HttpCase**: For testing controllers and web interfaces
- **SavepointCase**: Similar to TransactionCase but with better performance for multiple tests

### Best Practices for Testing

1. **Test in isolation**: Each test should be independent of others
2. **Use setUp for common setup**: Initialize test data in the setUp method
3. **Test one thing per method**: Each test method should test a single feature
4. **Use descriptive method names**: Name tests according to what they're testing
5. **Add docstrings**: Explain what each test is checking
6. **Clean up after tests**: If your tests create data that isn't automatically cleaned up, ensure it's removed

---

## Development Guidelines

### Code Style

- Follow [PEP8](https://peps.python.org/pep-0008/) for Python code
- Use [ESLint](https://eslint.org/) for JavaScript code
- Use 4 spaces for indentation (not tabs)
- Maximum line length of 120 characters
- Add docstrings to all methods and classes

### Naming Conventions

- Model names: lowercase with dots (e.g., `club.member`)
- Field names: lowercase with underscores (e.g., `member_name`)
- Method names: lowercase with underscores (e.g., `compute_name`)
- Class names: CamelCase (e.g., `ClubMember`)
- Module name: snake_case (e.g., `an_ClubMgnt`)

### Git Workflow

1. Create a branch for each feature or bugfix
2. Write descriptive commit messages
3. Submit pull requests for review
4. Ensure tests pass before merging

### Debugging

- Use the Odoo developer mode (add `?debug=1` to the URL)
- Check the Odoo logs for errors
- Use the Python debugger (`pdb`) for complex issues
- For JavaScript debugging, use browser developer tools

---

## Module Structure

The `an_ClubMgnt` module follows the standard Odoo module structure:

```
an_ClubMgnt/
│
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── club.py
│   ├── club_registration.py
│   ├── event.py
│   ├── event_mail.py
│   ├── res_partner.py
│   ├── sale_order.py
│   └── website.py
├── controllers/
│   ├── __init__.py
│   ├── club_page.py
│   ├── main.py
│   └── portal.py
├── views/
│   ├── club_menu.xml
│   ├── club_registration.xml
│   ├── club_report.xml
│   ├── club_templates.xml
│   ├── club_views.xml
│   ├── feuille_match.xml
│   ├── layout_template.xml
│   ├── loadscript.xml
│   ├── portal_templates.xml
│   └── website_templates.xml
├── static/
│   └── src/
│       ├── css/
│       │   ├── backend.css
│       │   ├── calendar.css
│       │   └── custom.css
│       ├── images/
│       │   ├── juventus.jpg
│       │   ├── rc.png
│       │   └── tete.png
│       ├── js/
│       │   └── event.js
│       └── xml/
│           └── registration.xml
├── security/
│   └── ir.model.access.csv
├── data/
│   └── mail_data.xml
├── wizard/
│   ├── __init__.py
│   ├── team_programmation.py
│   └── wizard_views.xml
└── tests/
    ├── __init__.py
    └── test_club_member.py
```

### Key Components

- **Models**: Define the data structure and business logic
- **Views**: Define the UI components
- **Controllers**: Handle web requests and responses
- **Security**: Define access rights
- **Data**: Define initial data
- **Wizard**: Define popup forms
- **Tests**: Define automated tests

---

## Resources

- [Odoo 17 Documentation](https://www.odoo.com/documentation/17.0/fr/)
- [OWL (Odoo Web Library)](https://github.com/odoo/owl)
- [Odoo Community Association Modules](https://github.com/OCA)

---

## Odoo Module Development Guidelines

The following guidelines are adapted from the Odoo guidelines document and should be followed when developing new modules or extending existing ones.

### 1. References

- **Version Odoo**: 17.0 Community ([Github](https://github.com/odoo/odoo))
- **Objective**: Generate standalone Odoo modules or extensions/modifications of workflows dependent on core modules.

### 2. Standard Module Structure

Respect the following structure for each generated module:

```
my_module/
│
├── manifest.py
├── models/
│ └── *.py
├── controllers/
│ └── *.py
├── views/
│ └── *.xml
├── static/
│ └── src/
│ ├── js/
│ └── css/
├── security/
│ └── *.csv
├── data/
│ └── *.xml
└── wizards/
└── *.py
```

### 3. __manifest__.py

- Declare all necessary dependencies in `depends`.
- Write a clear and precise description.
- Fill in all metadata (author, license, version...).
- Categorize the module correctly.

### 4. Inheritance and Extensions

#### a. QWeb

- Use `<xpath>` tags to target elements to modify, never duplicate code.
- Prefer `<t t-extend="template_name">` to override templates.
- Always target templates by `t-name` or stable structure.

#### b. Models (Python)

- Extend with `_inherit` rather than complete override.
- Maintain multi-inheritance compatibility.
- For a standalone module, only reference core models explicitly listed in dependencies.

#### c. Controllers (Python)

- Extend via `_inherit` or add new endpoints (routes).
- Document each security modification (authentication, access rights).

#### d. Javascript (OWL)

- Extend OWL components via `extends` or props injection.
- Place JS in `/static/src/js/`.
- Use only public OWL APIs.
- Write code in ES6.

### 5. Dependency Management

- **Standalone module**: depends only on `base` (except in special cases).
- **Extension**: document and explicitly reference necessary modules in the manifest.

### 6. Quality and Conventions

- Follow [PEP8](https://peps.python.org/pep-0008/) for Python, [ESLint](https://eslint.org/) for JS.
- Add explanatory comments on inheritances or complex parts.
- Integrate tests (unit, integration) if possible.
- Manage access rights via Odoo security groups.

### 7. Important Reminders

- Always prefer inheritance/extension to direct modification of the core.
- Respect modularity to ensure compatibility and maintainability.