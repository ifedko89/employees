import client from './client'

export function listDepartments() {
  return client.get('/departments')
}

export function createDepartment(name) {
  return client.post('/departments', { name })
}

export function updateDepartment(id, name) {
  return client.put(`/departments/${id}`, { name })
}

export function deleteDepartment(id) {
  return client.delete(`/departments/${id}`)
}
