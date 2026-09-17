pipeline {
    agent any

    options {
        disableConcurrentBuilds()
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
                set -eu

                echo "=== Checking secret files ==="

                for secret_file in .env .runtime.env deploy/blogpilot-production.env; do
                    if git ls-files --error-unmatch "$secret_file" >/dev/null 2>&1; then
                        echo "ERROR: Secret file is tracked by Git: $secret_file"
                        exit 1
                    fi
                done

                echo "Secret file check passed."

                echo "=== Checking production files ==="

                if [ ! -f docker-compose.prod.yml ]; then
                    echo "ERROR: docker-compose.prod.yml not found"
                    exit 1
                fi

                if [ ! -f deploy/production.env.example ]; then
                    echo "ERROR: deploy/production.env.example not found"
                    exit 1
                fi

                echo "Production files check passed."
                echo "=== Secret hygiene check PASSED ==="
            '''
        }
    }

    stage('API tests') {
        steps {
            sh '''#!/usr/bin/env bash
                set -euo pipefail

                docker build --tag "$API_TEST_IMAGE" apps/api

                docker run --rm \
                --network none \
                -e SECRET_KEY="ci-test-secret-key-123456789" \
                "$API_TEST_IMAGE" pytest -q
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
