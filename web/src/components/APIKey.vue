<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import axios from 'axios';
import { ElNotification, ElMessageBox } from 'element-plus';
import { Delete, Refresh, DocumentAdd } from '@element-plus/icons-vue';

const keyList = ref([]);
const loading = ref(false);
const searchQuery = ref('');

function refreshKeyList() {
    loading.value = true;
    axios.get('/api/key/list')
        .then(res => {
            if (res.data.code === 0) {
                keyList.value = res.data.data.map(key => ({
                    ...key,
                    created_at: new Date(key.created_at * 1000).toLocaleString()
                }));
                ElNotification({
                    message: 'Successfully refreshed key list.',
                    type: 'success',
                    duration: 1800
                });
            } else {
                throw new Error(res.data.message);
            }
        })
        .catch(err => {
            console.error(err);
            ElNotification({
                message: 'Failed to refresh key list.',
                type: 'error'
            });
        })
        .finally(() => {
            loading.value = false;
        });
}

function copyKey(key_id) {
    axios.get('/api/key/raw/' + key_id)
        .then(res => {
            if (res.data.code === 0) {
                ElMessageBox.alert(res.data.data.key, 'API Key', {
                    confirmButtonText: 'OK',
                });
            } else {
                throw new Error(res.data.message);
            }
        })
        .catch(err => {
            console.error(err);
            ElNotification({
                message: 'Failed to retrieve key.',
                type: 'error'
            });
        });
}

function createKey() {
    ElMessageBox.prompt('Please enter the name of your key:', 'Add Key', {
        confirmButtonText: 'OK',
        cancelButtonText: 'Cancel',
        inputPattern: /^[A-Za-z0-9\-_\.@]+$/,
        inputErrorMessage: 'Invalid key name (A-Z a-z 0-9 - _ . @ only)',
    }).then(({ value }) => {
        axios.post('/api/key/create', { name: value })
            .then(res => {
                if (res.data.code === 0) {
                    refreshKeyList();
                    ElMessageBox.alert(res.data.data.raw, 'API Key', {
                        confirmButtonText: 'OK',
                    });
                } else {
                    throw new Error(res.data.message);
                }
            })
            .catch(err => {
                console.error(err);
                ElNotification({
                    message: 'Failed to create key.',
                    type: 'error'
                });
            });
    }).catch(() => {});
}

function deleteKeyConfirmed(key_id) {
    axios.delete('/api/key/revoke/' + key_id)
        .then(res => {
            if (res.data.code === 0) {
                refreshKeyList();
                ElNotification({
                    message: 'Successfully deleted key.',
                    type: 'success'
                });
            } else {
                throw new Error(res.data.message);
            }
        })
        .catch(err => {
            console.error(err);
            ElNotification({
                message: 'Failed to delete key.',
                type: 'error'
            });
        });
}

onMounted(() => {
    refreshKeyList();
});
</script>

<template>
    <div class="key-manager">
        <el-card class="toolbar">
            <el-row :gutter="20">
                <el-col :xs="24" :sm="8" :md="6" :lg="4" :xl="4">
                    <el-input
                        v-model="searchQuery"
                        placeholder="Search keys"
                        prefix-icon="Search"
                    />
                </el-col>
                <el-col :xs="24" :sm="16" :md="18" :lg="20" :xl="20">
                    <el-button-group>
                        <el-button type="primary" @click="createKey" :icon="DocumentAdd">
                            Add Key
                        </el-button>
                        <el-button type="success" @click="refreshKeyList" :icon="Refresh" :loading="loading">
                            Refresh
                        </el-button>
                    </el-button-group>
                </el-col>
            </el-row>
        </el-card>

        <el-table
            :data="keyList.filter(key => key.name.toLowerCase().includes(searchQuery.toLowerCase()) || key.brief.toLowerCase().includes(searchQuery.toLowerCase()))"
            style="width: 100%"
            v-loading="loading"
        >
            <el-table-column prop="id" label="ID" width="80" sortable />
            <el-table-column prop="name" label="Name" sortable />
            <el-table-column prop="brief" label="Brief" sortable />
            <el-table-column prop="created_at" label="Create Time" width="180" sortable />
            <el-table-column label="Operations" width="200">
                <template #default="scope">
                    <el-button-group>
                        <el-button 
                            type="primary"
                            @click="copyKey(scope.row.id)"
                            size="small"
                        >
                            View Key
                        </el-button>
                        <el-button 
                            type="danger"
                            @click="deleteKeyConfirmed(scope.row.id)"
                            :icon="Delete"
                            size="small"
                        />
                    </el-button-group>
                </template>
            </el-table-column>
        </el-table>
    </div>
</template>

<style scoped>
.key-manager {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

.toolbar {
    margin-bottom: 20px;
}

.el-button-group {
    margin-top: 10px;
}

@media (max-width: 768px) {
    .el-button-group {
        display: flex;
        flex-direction: column;
    }

    .el-button-group .el-button {
        margin-left: 0 !important;
        margin-top: 10px;
    }
}

.el-table {
    margin-top: 20px;
}
</style>