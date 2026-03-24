import { createRouter, createWebHistory } from 'vue-router'
import EmployeeList from '../views/EmployeeList.vue'
import EmployeeForm from '../views/EmployeeForm.vue'
import EmployeeHistory from '../views/EmployeeHistory.vue'
import ReferenceList from '../views/ReferenceList.vue'

const routes = [
  { path: '/', name: 'home', component: EmployeeList },
  { path: '/create', name: 'create', component: EmployeeForm },
  { path: '/edit/:id', name: 'edit', component: EmployeeForm },
  { path: '/history/:id', name: 'history', component: EmployeeHistory },
  { path: '/positions', name: 'positions', component: ReferenceList, meta: { type: 'positions' } },
  { path: '/departments', name: 'departments', component: ReferenceList, meta: { type: 'departments' } },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
