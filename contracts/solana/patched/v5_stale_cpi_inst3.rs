// V5: Stale account data after CPI - Instance 3 (PATCHED)
// Fix: reload() the counter account after any CPI that modifies it
// before re-reading its fields as guard conditions.

use anchor_lang::prelude::*;

declare_id!("STALEV3111111111111111111111111111111111111");

#[program]
pub mod parent_program {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>) -> Result<()> {
        let counter = &mut ctx.accounts.counter;
        counter.value = 0;
        counter.processed = false;
        counter.bump = *ctx.bumps.get("counter").unwrap();
        Ok(())
    }

    pub fn process_once(ctx: Context<ProcessAction>) -> Result<()> {
        require!(
            !ctx.accounts.counter.processed,
            ProcessError::AlreadyProcessed
        );

        {
            let counter = &mut ctx.accounts.counter;
            counter.processed = true;
            counter.value = counter.value.checked_add(1).ok_or(ProcessError::Overflow)?;
        }

        // FIX: reload() ensures any subsequent guard reads reflect on-chain truth.
        ctx.accounts.counter.reload()?;

        // After reload, processed == true — a second call within the same
        // transaction would correctly fail the require! guard.
        require!(
            ctx.accounts.counter.processed,
            ProcessError::ReloadFailed
        );

        Ok(())
    }
}

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(
        init,
        payer = payer,
        space = 8 + Counter::SIZE,
        seeds = [b"counter"],
        bump
    )]
    pub counter: Account<'info, Counter>,
    #[account(mut)]
    pub payer: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct ProcessAction<'info> {
    #[account(mut, seeds = [b"counter"], bump = counter.bump)]
    pub counter: Account<'info, Counter>,
    pub user: Signer<'info>,
}

#[account]
pub struct Counter {
    pub value: u64,
    pub processed: bool,
    pub bump: u8,
}

impl Counter {
    pub const SIZE: usize = 8 + 1 + 1;
}

#[error_code]
pub enum ProcessError {
    #[msg("Action already processed")]
    AlreadyProcessed,
    #[msg("Arithmetic overflow")]
    Overflow,
    #[msg("Reload did not reflect expected state")]
    ReloadFailed,
}
