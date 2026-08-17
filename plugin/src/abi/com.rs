use super::vtables::*;
use std::marker::PhantomData;
use std::ptr;

pub trait Unknown {
    unsafe fn add_ref(this: *mut Self) -> i32;
    unsafe fn release(this: *mut Self) -> i32;
}

macro_rules! impl_unknown {
    ($ty:ty) => {
        impl Unknown for $ty {
            unsafe fn add_ref(this: *mut Self) -> i32 {
                if this.is_null() {
                    return 0;
                }
                let vtable = (*this).vtable;
                ((*vtable).add_ref)(this)
            }
            unsafe fn release(this: *mut Self) -> i32 {
                if this.is_null() {
                    return 0;
                }
                let vtable = (*this).vtable;
                ((*vtable).release)(this)
            }
        }
    };
}

impl_unknown!(Base);
impl_unknown!(Command);
impl_unknown!(Context);
impl_unknown!(Document);
impl_unknown!(UndoBuffer);
impl_unknown!(Chart);
impl_unknown!(Note);
impl_unknown!(Event);
impl_unknown!(EventBpm);
impl_unknown!(EventBeat);
impl_unknown!(EventTls);
impl_unknown!(EventNsm);

pub struct ComPtr<T: Unknown> {
    ptr: *mut T,
    _marker: PhantomData<T>,
}

impl<T: Unknown> ComPtr<T> {
    pub fn null() -> Self {
        Self {
            ptr: ptr::null_mut(),
            _marker: PhantomData,
        }
    }

    pub unsafe fn from_raw(ptr: *mut T) -> Self {
        Self {
            ptr,
            _marker: PhantomData,
        }
    }

    pub unsafe fn retain(ptr: *mut T) -> Self {
        if !ptr.is_null() {
            T::add_ref(ptr);
        }
        Self::from_raw(ptr)
    }

    pub fn as_ptr(&self) -> *mut T {
        self.ptr
    }

    pub fn is_null(&self) -> bool {
        self.ptr.is_null()
    }

    pub fn as_ref(&self) -> Option<&T> {
        if self.ptr.is_null() {
            None
        } else {
            unsafe { Some(&*self.ptr) }
        }
    }

    pub fn into_raw(mut self) -> *mut T {
        let ptr = self.ptr;
        self.ptr = ptr::null_mut();
        ptr
    }
}

impl<T: Unknown> Clone for ComPtr<T> {
    fn clone(&self) -> Self {
        unsafe { Self::retain(self.ptr) }
    }
}

impl<T: Unknown> Drop for ComPtr<T> {
    fn drop(&mut self) {
        if !self.ptr.is_null() {
            unsafe {
                T::release(self.ptr);
            }
            self.ptr = ptr::null_mut();
        }
    }
}

unsafe impl<T: Unknown> Send for ComPtr<T> {}
unsafe impl<T: Unknown> Sync for ComPtr<T> {}
