// Les 30: de pipeline als code. Declaratief, zelfde stappen als .github/workflows/ci.yml (les 24).
pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 20, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
        disableConcurrentBuilds()
    }

    environment {
        // Jenkins draait met een kaal PATH (service-stijl): uv en node staan er niet op
        PATH = "${env.HOME}/.local/bin:/opt/homebrew/bin:${env.PATH}"
        DJANGO_SETTINGS_MODULE = 'projectkaart.settings.test'
        DJANGO_DEBUG           = '0'
        DJANGO_ALLOWED_HOSTS   = 'localhost'
        // PostGIS uit het lab; pytest-django maakt zelf test_djangolab aan
        DB_NAME = 'djangolab'
        DB_HOST = '127.0.0.1'
        DB_PORT = '5433'
        // Secret text uit de Jenkins-credentials; Jenkins maskeert de waarde in de console
        DJANGO_SECRET_KEY = credentials('django-secret-key')
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git log -1 --format="commit %h  %an  %s"'
            }
        }

        stage('Lint') {
            steps {
                sh '''
                    uv sync --locked
                    uv run ruff check .
                    uv run ruff format --check .
                '''
            }
        }

        stage('Test') {
            steps {
                // De templates lezen het Vite-manifest; zonder build falen de view-tests
                sh 'cd frontend && npm ci && npm run build'
                sh '''
                    mkdir -p reports
                    uv run pytest -q \
                        --junitxml=reports/junit.xml \
                        --cov --cov-report=xml:reports/coverage.xml --cov-report=term
                '''
            }
        }

        stage('Build') {
            steps {
                sh 'uv build --wheel'
                archiveArtifacts artifacts: 'dist/*.whl', fingerprint: true
            }
        }

        stage('Sonar') {
            // les 31/32: SonarQube-scan en kwaliteitspoort
            when { expression { false } }
            steps {
                echo 'Sonar volgt in les 31'
            }
        }

        stage('Publish') {
            // les 31/32: wheel naar Nexus
            when { expression { false } }
            steps {
                echo 'Publish volgt in les 32'
            }
        }
    }

    post {
        always {
            junit testResults: 'reports/junit.xml', allowEmptyResults: true
            recordCoverage(
                tools: [[parser: 'COBERTURA', pattern: 'reports/coverage.xml']],
                sourceCodeRetention: 'NEVER'
            )
        }
    }
}
