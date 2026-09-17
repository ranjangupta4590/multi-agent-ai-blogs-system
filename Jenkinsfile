pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        disableResume()
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '20', daysToKeepStr: '14'))
        skipDefaultCheckout(true)
    }

    environment {
        API_TEST_IMAGE = "blogpilot-api-test:${BUILD_NUMBER}"
        WEB_TEST_IMAGE = "blogpilot-web-test:${BUILD_NUMBER}"
        RUNTIME_ENV = '.runtime.env'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Verify secret hygiene') {
            steps {
                sh '''#!/usr/bin/env bash
                    set -euo pipefail
                    if git ls-files | while IFS= read -r file; do
                      case "$file" in
                        .env|*/.env|*.env|*.env.local|*.env.development.local|*.env.test.local|*.env.production|*.env.production.local|*.pem|*.p12|*.pfx|*.key|*/id_rsa|*/id_ed25519)
                          echo "Refusing deployment: a secret-like file is tracked by Git: $file" >&2
                          exit 1
                          ;;
                      esac
                    done
                    then
                      :
                    else
                      exit 1
                    fi
                    test -f docker-compose.prod.yml
                    test -f deploy/production.env.example
                '''
            }
        }

        stage('API tests') {
            steps {
                sh '''#!/usr/bin/env bash
                    set -euo pipefail
                    docker build --tag "$API_TEST_IMAGE" apps/api
                    docker run --rm --network none "$API_TEST_IMAGE" pytest -q
                '''
            }
        }

        stage('Web type check and build') {
            steps {
                sh '''#!/usr/bin/env bash
                    set -euo pipefail
                    docker build \
                      --build-arg NEXT_PUBLIC_API_URL=https://blogpilot.duckdns.org/api/v1 \
                      --tag "$WEB_TEST_IMAGE" \
                      apps/web
                '''
            }
        }

        stage('Deploy production') {
            steps {
                withCredentials([file(credentialsId: 'blogpilot-production-env', variable: 'PRODUCTION_ENV_FILE')]) {
                    sh '''#!/usr/bin/env bash
                        set -euo pipefail
                        set +x
                        install -m 600 "$PRODUCTION_ENV_FILE" "$RUNTIME_ENV"
                        trap 'rm -f "$RUNTIME_ENV"' EXIT

                        docker compose --env-file "$RUNTIME_ENV" \
                          -f docker-compose.yml -f docker-compose.prod.yml config -q
                        docker compose --env-file "$RUNTIME_ENV" \
                          -f docker-compose.yml -f docker-compose.prod.yml up -d --build --remove-orphans

                        for attempt in $(seq 1 30); do
                          if curl --fail --silent --show-error --max-time 5 http://127.0.0.1:8000/health >/dev/null; then
                            exit 0
                          fi
                          sleep 2
                        done
                        echo 'API health check did not succeed after deployment.' >&2
                        exit 1
                    '''
                }
            }
        }
    }

    post {
        always {
            cleanWs(deleteDirs: true, disableDeferredWipeout: true, notFailBuild: true)
        }
    }
}
