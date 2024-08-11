<script setup>
import { ref, onMounted } from "vue";
import axios from "axios";
import { ElSkeleton } from 'element-plus';

const version = ref("");
const loading = ref(true);

function getVersion() {
    axios.get("/api/info/version")
        .then((res) => {
            version.value = res.data.data;
            loading.value = false;
        })
        .catch(() => {
            version.value = "Error";
            loading.value = false;
        });
}

onMounted(() => {
    getVersion();
});
</script>

<template>
    <div class="home">
        <el-card class="home-card" :body-style="{ padding: '0px' }">
            <el-skeleton :loading="loading" animated>
                <template #template>
                    <div style="padding: 20px">
                        <el-skeleton-item variant="h1" style="width: 50%" />
                        <el-skeleton-item variant="text" style="margin-top: 16px" />
                        <el-skeleton-item variant="text" style="margin-top: 16px" />
                    </div>
                </template>
                <template #default>
                    <div class="card-content">
                        <div class="header">
                            <h1>llm-api</h1>
                            <el-tag v-if="version" type="success" size="small" effect="dark">{{ version }}</el-tag>
                        </div>
                        <div class="body">
                            <p>
                                Makes reverse engineering LLM libs a OpenAI format API.
                            </p>
                            <p>
                                Built by <a href="https://github.com/Metimol1" target="_blank" rel="noopener noreferrer">Metimol</a>
                            </p>
                        </div>
                        <div class="footer">
                            <el-button type="primary" @click="$router.push('/channel')">Manage Channels</el-button>
                            <el-button type="info" @click="$router.push('/apikey')">API Keys</el-button>
                        </div>
                    </div>
                </template>
            </el-skeleton>
        </el-card>
    </div>
</template>

<style scoped>
.home {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: calc(100vh - 60px);
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.home-card {
    width: 100%;
    max-width: 600px;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1), 0 1px 3px rgba(0, 0, 0, 0.08);
    transition: all 0.3s ease;
}

.home-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 7px 14px rgba(0, 0, 0, 0.1), 0 3px 6px rgba(0, 0, 0, 0.08);
}

.card-content {
    padding: 20px;
}

.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

.header h1 {
    margin: 0;
    font-size: 2.5rem;
    color: #303133;
}

.body {
    margin-bottom: 20px;
}

.body p {
    margin: 10px 0;
    color: #606266;
    line-height: 1.6;
}

.body a {
    color: #409EFF;
    text-decoration: none;
    font-weight: bold;
    transition: color 0.3s ease;
}

.body a:hover {
    color: #66b1ff;
}

.footer {
    display: flex;
    justify-content: flex-start;
    gap: 10px;
}

@media (max-width: 600px) {
    .home-card {
        margin: 0 20px;
    }

    .header h1 {
        font-size: 2rem;
    }

    .footer {
        flex-direction: column;
    }

    .footer .el-button {
        width: 100%;
    }
}
</style>