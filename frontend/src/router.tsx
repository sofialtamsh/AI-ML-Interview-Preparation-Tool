import { lazy, Suspense, type ReactNode } from 'react'
import { createBrowserRouter, Navigate, Outlet } from 'react-router'

import { AdminLayout } from './admin/AdminLayout'
import { RequireAdmin, RequirePermission } from './admin/RequireAdmin'
import { FullPageLoader } from './components/ui/Feedback'
import { RedirectIfStudent, RequireStudent } from './student/RequireStudent'
import { StudentLayout } from './student/StudentLayout'

// Every page is its own chunk, so students never download admin screens (and vice versa).
const LandingPage = lazy(() => import('./pages/LandingPage'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'))

const StudentLogin = lazy(() => import('./student/pages/LoginPage'))
const StudentRegister = lazy(() => import('./student/pages/RegisterPage'))
const ForgotPassword = lazy(() => import('./student/pages/ForgotPasswordPage'))
const ResetPassword = lazy(() => import('./student/pages/ResetPasswordPage'))
const StudentDashboard = lazy(() => import('./student/pages/DashboardPage'))
const StudentProfile = lazy(() => import('./student/pages/ProfilePage'))

const AdminLogin = lazy(() => import('./admin/pages/LoginPage'))
const AdminChangePassword = lazy(() => import('./admin/pages/ChangePasswordPage'))
const AdminOverview = lazy(() => import('./admin/pages/OverviewPage'))
const AdminStudents = lazy(() => import('./admin/pages/StudentsPage'))
const AdminStudentDetail = lazy(() => import('./admin/pages/StudentDetailPage'))
const SettingsLayout = lazy(() => import('./admin/pages/settings/SettingsLayout'))
const AdminsTab = lazy(() => import('./admin/pages/settings/AdminsTab'))
const RolesTab = lazy(() => import('./admin/pages/settings/RolesTab'))
const AuditTab = lazy(() => import('./admin/pages/settings/AuditTab'))
const UsageTab = lazy(() => import('./admin/pages/settings/UsageTab'))

const guest = (page: ReactNode) => <RedirectIfStudent>{page}</RedirectIfStudent>
const allow = (anyOf: string[], page: ReactNode) => (
  <RequirePermission anyOf={anyOf}>{page}</RequirePermission>
)

function Root() {
  return (
    <Suspense fallback={<FullPageLoader />}>
      <Outlet />
    </Suspense>
  )
}

export const router = createBrowserRouter([
  {
    element: <Root />,
    children: [
      { path: '/', element: <LandingPage /> },
      { path: '/login', element: guest(<StudentLogin />) },
      { path: '/register', element: guest(<StudentRegister />) },
      { path: '/forgot-password', element: guest(<ForgotPassword />) },
      { path: '/reset-password', element: <ResetPassword /> },
      {
        path: '/app',
        element: (
          <RequireStudent>
            <StudentLayout />
          </RequireStudent>
        ),
        children: [
          { index: true, element: <StudentDashboard /> },
          { path: 'profile', element: <StudentProfile /> },
        ],
      },

      { path: '/admin/login', element: <AdminLogin /> },
      {
        path: '/admin/change-password',
        element: (
          <RequireAdmin passwordChangePage>
            <AdminChangePassword />
          </RequireAdmin>
        ),
      },
      {
        path: '/admin',
        element: (
          <RequireAdmin>
            <AdminLayout />
          </RequireAdmin>
        ),
        children: [
          { index: true, element: <AdminOverview /> },
          { path: 'students', element: allow(['students.view'], <AdminStudents />) },
          { path: 'students/:id', element: allow(['students.view'], <AdminStudentDetail />) },
          {
            path: 'settings',
            element: allow(['admins.manage', 'roles.manage', 'audit.view', 'ai_usage.view'], <SettingsLayout />),
            children: [
              { path: 'admins', element: allow(['admins.manage'], <AdminsTab />) },
              { path: 'roles', element: allow(['admins.manage', 'roles.manage'], <RolesTab />) },
              { path: 'audit', element: allow(['audit.view'], <AuditTab />) },
              { path: 'usage', element: allow(['ai_usage.view'], <UsageTab />) },
            ],
          },
          { path: '*', element: <Navigate to="/admin" replace /> },
        ],
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
