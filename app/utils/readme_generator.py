"""
README.md Generator for MultiAgent Projects

Automatically generates comprehensive README.md files for generated projects.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class ReadmeGenerator:
    """Generates comprehensive README.md files for projects."""
    
    def __init__(self, project_dir: str, project_name: str):
        """
        Initialize README generator.
        
        Args:
            project_dir: Path to the project directory
            project_name: Name of the project
        """
        self.project_dir = Path(project_dir)
        self.project_name = project_name
        self.backend_dir = self.project_dir / "backend"
        self.frontend_dir = self.project_dir / "frontend"
        
    def detect_technologies(self) -> Dict[str, List[str]]:
        """Detect technologies used in the project."""
        tech = {
            "backend": [],
            "frontend": [],
            "database": [],
            "tools": []
        }
        
        # Backend detection
        if (self.backend_dir / "*.csproj").parent.exists():
            csproj_files = list(self.backend_dir.glob("*.csproj"))
            if csproj_files:
                tech["backend"].append(".NET Core/ASP.NET Core")
                tech["backend"].append("C#")
        
        # Frontend detection
        if (self.frontend_dir / "package.json").exists():
            tech["frontend"].append("React")
            tech["frontend"].append("TypeScript/JavaScript")
            tech["frontend"].append("Node.js")
        
        # Database detection
        backend_files = list(self.backend_dir.glob("**/*.cs")) if self.backend_dir.exists() else []
        for file in backend_files:
            content = file.read_text(encoding='utf-8', errors='ignore')
            if "PostgreSQL" in content or "Npgsql" in content:
                if "PostgreSQL" not in tech["database"]:
                    tech["database"].append("PostgreSQL")
            if "Redis" in content or "StackExchange.Redis" in content:
                if "Redis" not in tech["database"]:
                    tech["database"].append("Redis (Cache)")
        
        # Tools
        if (self.project_dir / "docker-compose.yml").exists():
            tech["tools"].append("Docker & Docker Compose")
        if (self.project_dir / ".git").exists():
            tech["tools"].append("Git")
            
        return tech
    
    def get_file_structure(self) -> str:
        """Generate file structure tree."""
        structure = []
        
        def add_tree(path: Path, prefix: str = "", is_last: bool = True):
            """Recursively build tree structure."""
            if path.name.startswith('.') and path.name not in ['.dockerignore']:
                return
            
            if path.name in ['node_modules', 'bin', 'obj', '__pycache__', '.git']:
                return
                
            connector = "└── " if is_last else "├── "
            structure.append(f"{prefix}{connector}{path.name}")
            
            if path.is_dir():
                children = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
                children = [c for c in children if not c.name.startswith('.') or c.name in ['.dockerignore']]
                children = [c for c in children if c.name not in ['node_modules', 'bin', 'obj', '__pycache__', '.git']]
                
                for i, child in enumerate(children):
                    is_last_child = i == len(children) - 1
                    extension = "    " if is_last else "│   "
                    add_tree(child, prefix + extension, is_last_child)
        
        structure.append(self.project_name + "/")
        items = sorted(self.project_dir.iterdir(), key=lambda x: (not x.is_dir(), x.name))
        items = [i for i in items if not i.name.startswith('.') or i.name in ['.dockerignore']]
        items = [i for i in items if i.name not in ['node_modules', 'bin', 'obj', '__pycache__', '.git']]
        
        for i, item in enumerate(items):
            add_tree(item, "", i == len(items) - 1)
        
        return "\n".join(structure)
    
    def detect_endpoints(self) -> List[str]:
        """Detect API endpoints from backend code."""
        endpoints = []
        
        if not self.backend_dir.exists():
            return endpoints
        
        controller_files = list(self.backend_dir.glob("**/*Controller.cs"))
        
        for file in controller_files:
            try:
                content = file.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')
                
                for i, line in enumerate(lines):
                    # Look for HTTP method attributes
                    if any(attr in line for attr in ['[HttpGet', '[HttpPost', '[HttpPut', '[HttpDelete', '[HttpPatch']):
                        method = None
                        if '[HttpGet' in line:
                            method = 'GET'
                        elif '[HttpPost' in line:
                            method = 'POST'
                        elif '[HttpPut' in line:
                            method = 'PUT'
                        elif '[HttpDelete' in line:
                            method = 'DELETE'
                        elif '[HttpPatch' in line:
                            method = 'PATCH'
                        
                        # Extract route from attribute
                        route = ""
                        if '("' in line:
                            route = line.split('("')[1].split('")')[0]
                        
                        # Get method name from next non-empty line
                        for j in range(i + 1, min(i + 5, len(lines))):
                            if 'public' in lines[j] and '(' in lines[j]:
                                method_name = lines[j].split('(')[0].split()[-1]
                                endpoint = f"{method:7s} /api/{route if route else method_name.lower()}"
                                if endpoint not in endpoints:
                                    endpoints.append(endpoint)
                                break
            except Exception:
                continue
        
        return endpoints
    
    def generate(self, requirement: Optional[str] = None) -> str:
        """
        Generate README.md content.
        
        Args:
            requirement: Original project requirement/description
            
        Returns:
            Complete README.md content
        """
        tech = self.detect_technologies()
        structure = self.get_file_structure()
        endpoints = self.detect_endpoints()
        
        has_backend = self.backend_dir.exists()
        has_frontend = self.frontend_dir.exists()
        has_docker = (self.project_dir / "docker-compose.yml").exists()
        
        readme = f"""# {self.project_name}

> Generated by MultiAgent Software Development System
> Created: {datetime.now().strftime('%Y-%m-%d')}

"""
        
        # Description
        if requirement:
            readme += f"""## 📋 Description

{requirement}

"""
        
        # Tech Stack
        readme += "## 🛠️ Technology Stack\n\n"
        
        if tech["backend"]:
            readme += "**Backend:**\n"
            for t in tech["backend"]:
                readme += f"- {t}\n"
            readme += "\n"
        
        if tech["frontend"]:
            readme += "**Frontend:**\n"
            for t in tech["frontend"]:
                readme += f"- {t}\n"
            readme += "\n"
        
        if tech["database"]:
            readme += "**Database & Cache:**\n"
            for t in tech["database"]:
                readme += f"- {t}\n"
            readme += "\n"
        
        if tech["tools"]:
            readme += "**Tools:**\n"
            for t in tech["tools"]:
                readme += f"- {t}\n"
            readme += "\n"
        
        # Prerequisites
        readme += "## 📦 Prerequisites\n\n"
        prereqs = []
        if has_docker:
            prereqs.append("- Docker & Docker Compose")
        else:
            if has_backend:
                prereqs.append("- .NET 8.0 SDK or later")
            if has_frontend:
                prereqs.append("- Node.js 18+ and npm")
            if "PostgreSQL" in tech["database"]:
                prereqs.append("- PostgreSQL 14+")
            if "Redis" in tech["database"]:
                prereqs.append("- Redis 7+")
        
        for p in prereqs:
            readme += f"{p}\n"
        readme += "\n"
        
        # Quick Start
        readme += "## 🚀 Quick Start\n\n"
        
        if has_docker:
            readme += """### Using Docker (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000

"""
        
        # Manual Setup
        if has_backend or has_frontend:
            readme += "### Manual Setup\n\n"
            
            if has_backend:
                readme += """#### Backend

```bash
cd backend

# Restore dependencies
dotnet restore

# Run the application
dotnet run
```

The API will be available at: http://localhost:5000

"""
            
            if has_frontend:
                readme += """#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

The frontend will be available at: http://localhost:3000

"""
        
        # API Endpoints
        if endpoints:
            readme += "## 🔌 API Endpoints\n\n"
            readme += "```\n"
            for endpoint in endpoints:
                readme += f"{endpoint}\n"
            readme += "```\n\n"
        
        # Project Structure
        readme += f"""## 📁 Project Structure

```
{structure}
```

"""
        
        # Development
        readme += "## 💻 Development\n\n"
        
        if has_backend:
            readme += """### Backend Development

```bash
cd backend

# Build the project
dotnet build

# Run tests (if available)
dotnet test

# Run with hot reload
dotnet watch run
```

"""
        
        if has_frontend:
            readme += """### Frontend Development

```bash
cd frontend

# Start development server with hot reload
npm start

# Build for production
npm run build

# Run tests (if available)
npm test
```

"""
        
        # Docker Commands
        if has_docker:
            readme += """## 🐳 Docker Commands

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f [service-name]

# Stop services
docker-compose stop

# Remove containers
docker-compose down

# Remove containers and volumes
docker-compose down -v

# Rebuild and restart
docker-compose up -d --build
```

"""
        
        # Environment Variables
        if has_backend or has_frontend:
            readme += """## ⚙️ Environment Variables

Create `.env` file in the project root (for Docker) or in respective directories:

"""
            
            if has_backend:
                readme += """**Backend (.env):**
```
ASPNETCORE_ENVIRONMENT=Development
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
REDIS_URL=localhost:6379
```

"""
            
            if has_frontend:
                readme += """**Frontend (.env):**
```
REACT_APP_API_URL=http://localhost:5000
```

"""
        
        # Troubleshooting
        readme += """## 🔧 Troubleshooting

### Common Issues

**Port already in use:**
```bash
# Check what's using the port
netstat -ano | findstr :5000

# Kill the process or change the port in configuration
```

**Docker issues:**
```bash
# Reset Docker environment
docker-compose down -v
docker-compose up -d --build
```

"""
        
        if has_backend:
            readme += """**Database connection issues:**
- Verify PostgreSQL is running
- Check connection string in appsettings.json
- Ensure database exists

"""
        
        # Additional Info
        readme += """## 📝 Notes

- This project was generated using the MultiAgent Software Development System
- The system used multiple AI agents (Designer, Backend, Frontend, QA) to create this application
- All code went through automated QA validation and build verification

## 🤝 Contributing

This is an auto-generated project. To modify:

1. Make changes to the code
2. Test thoroughly
3. Update this README if needed
4. Commit your changes

## 📄 License

This project is generated for development purposes.

---

**Generated on:** """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """
**System:** MultiAgent Software Development System v1.0
"""
        
        return readme
    
    def save(self, requirement: Optional[str] = None) -> Path:
        """
        Generate and save README.md file.
        
        Args:
            requirement: Original project requirement/description
            
        Returns:
            Path to the saved README.md file
        """
        content = self.generate(requirement)
        readme_path = self.project_dir / "README.md"
        
        readme_path.write_text(content, encoding='utf-8')
        
        return readme_path
