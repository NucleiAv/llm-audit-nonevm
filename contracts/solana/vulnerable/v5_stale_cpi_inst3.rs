// V5: Stale account data after CPI - Instance 3 (variant)
// Subtler: The stale data issue is in a custom program account (not a token
// account). After a CPI that increments a counter in a child program's account,
// the parent reads its own stale copy and uses it as a guard condition,
// allowing the same action to be executed twice in one transaction.

use anchor_lang::prelude::*;

declare_id!("STALEV3111111111111111111111111111111111111");

// Simulated child program CPI (same program in this example for simplicity).
const CHILD_PROGRAM_ID: &str = "CHILD111111111111111111111111111111111111111";

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

    // BUG: After the CPI that sets counter.processed = true on-chain,
    // the parent still reads the stale deserialized state where processed = false.
    // A second call within the same transaction passes the guard again.
    pub fn process_once(ctx: Context<ProcessAction>) -> Result<()> {
        // Guard using potentially stale state.
        require!(
            !ctx.accounts.counter.processed,
            ProcessError::AlreadyProcessed
        );

        // CPI sets counter.processed = true on-chain (simulated here as direct write).
        // In a real scenario this would be an invoke() to a child program.
        {
            let counter = &mut ctx.accounts.counter;
            counter.processed = true;
            counter.value = counter.value.wrapping_add(1);
        }

        // BUG: After the above mutation via simulated CPI, re-reading the
        // account in a second instruction call in the same transaction would
        // still see processed = false if reload() was not called
        // (this simulates what happens when the mutation occurs via actual CPI).

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
}
